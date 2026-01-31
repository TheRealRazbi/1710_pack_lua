from __future__ import annotations


class _LuaApiFunc:
    """
    Small descriptor used only for transpilation.
    At runtime in Python it can be a stub (raises), but the
    transpiler can inspect its attributes.
    """

    def __init__(self, lua_table: str, lua_name: str):
        self.lua_table = lua_table        # e.g. "peripheral"
        self.lua_name = lua_name          # e.g. "getNames"

    def __call__(self, *args, **kwargs):
        # Optional: crash loudly if run directly in Python.
        raise RuntimeError(
            f"This API function is only meant to be used with the transpiler "
            f"(Lua: {self.lua_table}.{self.lua_name})."
        )


class Peripheral:
    # Python: peripheral.get_names()
    # Lua:    peripheral.getNames()
    get_names = _LuaApiFunc(lua_table="peripheral", lua_name="getNames")

    # Example of more mappings you might add later:
    # get_type = _LuaApiFunc(lua_table="peripheral", lua_name="getType")
    # wrap = _LuaApiFunc(lua_table="peripheral", lua_name="wrap")
    # is_present = _LuaApiFunc(lua_table="peripheral", lua_name="isPresent")
    # ...etc...


peripheral = Peripheral()
# Transpiler hint: for any attribute on `peripheral` that is an instance
# of _LuaApiFunc, translate `peripheral.attr_name(...)` to
# `peripheral.<lua_name>(...)` in the generated Lua.
