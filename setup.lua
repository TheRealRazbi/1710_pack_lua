-- this script is meant to setup the pull command on CC
-- execute with openp/github run TheRealRazbi 1710_pack_lua main setup.lua

local path = "/pull"
shell.run("cd", "/")
if not fs.exists(path) then
    shell.run("openp/github", "get", "TheRealRazbi", "1710_pack_lua", "main", "pull.lua", "/pull")
    print("Installed `pull` in /pull")
else
    print("/pull already exists")
end
print("Running pull...")
shell.run("pull")