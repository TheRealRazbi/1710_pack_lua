-- this script is meant to update main.lua
shell.run("cd", "/")
local ok = shell.run("openp/github", "get", "TheRealRazbi", "1710_pack_lua", "main", "main.lua", "/main.new")
if ok then
	shell.run("rm main")
	shell.run("mv main.new main")
	print("Update 'main' successfully. Run with 'main'")
else
	print("Download failed, not updating main")
end
