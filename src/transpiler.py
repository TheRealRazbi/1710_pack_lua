import ast
from pathlib import Path

SRC_FILE = Path("transpiler_in.py")
OUT_FILE = Path("transpiler_out.lua")


class PyToLua(ast.NodeVisitor):
    def __init__(self):
        self.lines = []
        self.indent = 0

    def emit(self, text: str) -> None:
        self.lines.append("    " * self.indent + text)

    # --- top level ---
    def visit_Module(self, node: ast.Module) -> None:
        for stmt in node.body:
            self.visit(stmt)

    # --- statements ---
    def visit_Expr(self, node: ast.Expr) -> None:
        self.emit(self.expr(node.value))

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            raise NotImplementedError("Only single assignment supported")
        target = self.expr(node.targets[0])
        value = self.expr(node.value)
        # Lua uses `local` for new variables; simple heuristic:
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

    # --- expressions ---
    def expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return f"\"{node.value}\""
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
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
            # direct mapping: print(...) -> print(...)
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
