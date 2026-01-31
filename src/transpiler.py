import ast
from os import getenv
from pathlib import Path

SRC_FILE = Path(getenv('in_file', "transpiler_in.py"))
OUT_FILE = Path(getenv('out_file', "transpiler_out.lua"))


def snake_to_camel(name: str) -> str:
    """
    Convert snake_case -> camelCase (first segment stays lowercase).
    Example: get_names -> getNames
    """
    parts = name.split("_")
    if not parts:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class PyToLua(ast.NodeVisitor):
    def __init__(self):
        self.lines = []
        self.indent = 0
        # Map of local symbol name -> (module, original_name)
        # e.g. {"peripheral": ("cc_lib", "peripheral")}
        self.imports: dict[str, tuple[str, str]] = {}
        # Track if we saw a `main` function so we can call it at end
        self.has_main = False

    def emit(self, text: str) -> None:
        self.lines.append("    " * self.indent + text)

    # --- top level ---
    def visit_Module(self, node: ast.Module) -> None:
        for stmt in node.body:
            self.visit(stmt)
        # Auto-call main if defined
        if self.has_main:
            self.emit("main()")

    # --- imports (to identify cc_lib API objects) ---
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # from cc_lib import peripheral
        module = node.module
        if module is None:
            return
        for alias in node.names:
            local = alias.asname or alias.name
            self.imports[local] = (module, alias.name)

    def visit_Import(self, node: ast.Import) -> None:
        # import cc_lib as lib  (less useful for direct API but we record anyway)
        for alias in node.names:
            local = alias.asname or alias.name
            self.imports[local] = (alias.name, None)

    # --- statements ---
    def visit_Expr(self, node: ast.Expr) -> None:
        self.emit(self.expr(node.value))

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            raise NotImplementedError("Only single assignment supported")
        target = self.expr(node.targets[0])
        value = self.expr(node.value)
        self.emit(f"local {target} = {value}")

    def visit_If(self, node: ast.If) -> None:
        cond = self.expr(node.test)
        self.emit(f"if {cond} then")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent -= 1
        if node.orelse:
            self.emit("else")
            self.indent += 1
            for stmt in node.orelse:
                self.visit(stmt)
            self.indent -= 1
        self.emit("end")

    def visit_While(self, node: ast.While) -> None:
        cond = self.expr(node.test)
        self.emit(f"while {cond} do")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent -= 1
        self.emit("end")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Very small subset: only simple positional args
        args = [arg.arg for arg in node.args.args]
        args_src = ", ".join(args)
        self.emit(f"function {node.name}({args_src})")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent -= 1
        self.emit("end")
        if node.name == "main":
            self.has_main = True

    # --- expressions ---
    def expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return f"\"{node.value}\""
            return repr(node.value)

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            # Handle object.attribute – we care especially about
            # imported cc_lib objects like `peripheral.get_names`
            value_src = self.expr(node.value)
            attr = node.attr
            # If base is an imported symbol from cc_lib, convert attr to camelCase.
            # Example Python:   peripheral.get_names
            # Becomes Lua:      peripheral.getNames
            if (
                isinstance(node.value, ast.Name)
                and node.value.id in self.imports
                and self.imports[node.value.id][0] == "cc_lib"
            ):
                lua_attr = snake_to_camel(attr)
                return f"{value_src}.{lua_attr}"
            # Fallback: keep attribute as-is
            return f"{value_src}.{attr}"

        if isinstance(node, ast.BinOp):
            left = self.expr(node.left)
            right = self.expr(node.right)
            op = self.binop(node.op)
            return f"({left} {op} {right})"

        if isinstance(node, ast.UnaryOp):
            operand = self.expr(node.operand)
            if isinstance(node.op, ast.USub):
                return f"(-{operand})"
            raise NotImplementedError("Only unary minus supported")

        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise NotImplementedError("Only simple comparisons supported")
            left = self.expr(node.left)
            right = self.expr(node.comparators[0])
            op = self.cmpop(node.ops[0])
            return f"({left} {op} {right})"

        if isinstance(node, ast.Call):
            func = self.expr(node.func)
            args = ", ".join(self.expr(a) for a in node.args)
            return f"{func}({args})"

        raise NotImplementedError(f"Unsupported expression: {ast.dump(node)}")

    def binop(self, op: ast.AST) -> str:
        if isinstance(op, ast.Add):
            return "+"
        if isinstance(op, ast.Sub):
            return "-"
        if isinstance(op, ast.Mult):
            return "*"
        if isinstance(op, ast.Div):
            return "/"
        raise NotImplementedError(f"Unsupported binop: {op}")

    def cmpop(self, op: ast.AST) -> str:
        if isinstance(op, ast.Eq):
            return "=="
        if isinstance(op, ast.NotEq):
            return "~="
        if isinstance(op, ast.Lt):
            return "<"
        if isinstance(op, ast.LtE):
            return "<="
        if isinstance(op, ast.Gt):
            return ">"
        if isinstance(op, ast.GtE):
            return ">="
        raise NotImplementedError(f"Unsupported cmpop: {op}")


def transpile_file(src: Path, dst: Path) -> None:
    code = src.read_text(encoding="utf8")
    tree = ast.parse(code, filename=str(src))
    compiler = PyToLua()
    compiler.visit(tree)
    dst.write_text("\n".join(compiler.lines), encoding="utf8")


if __name__ == "__main__":
    if not SRC_FILE.exists():
        raise SystemExit(f"Source file {SRC_FILE} not found")
    transpile_file(SRC_FILE, OUT_FILE)
    print(f"Transpiled {SRC_FILE} -> {OUT_FILE}")
