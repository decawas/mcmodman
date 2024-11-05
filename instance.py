# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606
import os, toml, re

def instance_firstrun():
	managefile = "# this instance is managed by mcmodman\n# please do not change any files that might break mcmodman"
	loaders = []

	if os.path.exists(os.path.expanduser(f"{instance_dir}/logs/latest.log")):
		log = open(os.path.expanduser(f"{instance_dir}/logs/latest.log"), "r", encoding="utf-8").read()
	else:
		print("instance must be run at least once before using mcmodman")
		raise SystemExit

	if os.path.exists(f"{instance_dir}/config/quilt-loader.txt"): # detect quilt
		loaders.append("quilt")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
	if os.path.exists(f"{instance_dir}/config/neoforge-client.toml") or os.path.exists(f"{instance_dir}/config/neoforge-server.toml"): # detect neoforge
		loaders.append("neoforge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
	if os.path.exists(f"{instance_dir}/.fabric"): # detect fabric
		loaders.append("fabric")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
	if os.path.exists(f"{instance_dir}/config/forge-client.toml") or os.path.exists(f"{instance_dir}/config/forge-server.toml"): # detect forge
		loaders.append("forge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
	if os.path.exists(f"{instance_dir}/config/liteconfig"): # detect liteloader
		loaders.append("liteloader")
		match = re.search(r'LiteLoader (\d+(?:\.\d+)*)\n', log)
	if re.search(r'Purpur (\d+(?:\.\d+)*)-', log) is not None: # detect folia
		loaders.append("purpur")
		match = re.search(r'Purpur (\d+(?:\.\d+)*)-', log)
	if re.search(r'Folia version (\d+(?:\.\d+)*)-', log) is not None: # detect folia
		loaders.append("folia")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
	if os.path.exists(f"{instance_dir}/config/paper-global.yml") and loaders[0] == any(["folia", "purpur"]): # detect paper
		loaders.append("paper")
		match = re.search(r'Paper (\d+(?:\.\d+)*)-', log)
	if os.path.exists(f"{instance_dir}/spigot.yml") and loaders[0] == any(["folia", "purpur", "paper"]): # detect spigot
		loaders.append("spigot")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
	if os.path.exists(f"{instance_dir}/bukkit.yml") and loaders[0] == any(["folia", "purpur", "paper", "spigot"]): # detect bukkit
		loaders.append("bukkit")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
	if os.path.exists(f"{instance_dir}/config/sponge/sponge.conf"): # detect sponge
		loaders.append("sponge")
		match = re.search(r'spongevanilla-(\d+(?:\.\d+)*)-', log)

	if len(loaders) > 1:
		print("mcmodman does not support instances with multiple loaders")
		return "Multiple Loader"
	if len(loaders) < 1:
		print("Could not find any mod loaders for this instance\nif you are using Rift, RML or have no mod loader you will have to manually set that")
		return "No Loader"
	managefile += f"\nloader = \"{loaders[0]}\""

	if loaders[0] == "purpur" or loaders[0] == "folia" or loaders[0] == "paper" or loaders[0] == "spigot" or loaders[0] == "bukkit":
		managefile += "\nmodfolder = \"plugins\""
	if loaders[0] == "quilt" or loaders[0] == "neoforge" or loaders[0] == "sponge" or loaders[0] == "fabric" or loaders[0] == "forge" or loaders[0] == "liteloader":
		managefile += "\nmodfolder = \"mods\""

	if match:
		managefile += f"\nversion = \"{match.group(1)}\""
	else:
		return "No version"

	if os.path.exists(f"{instance_dir}/crafty_managed.txt"):
		print("WARNING: THIS INSTANCE IS MANAGED BY CRAFTY CONTROLLER\nUSING mcmodman ON THIS INSTANCE MAY BREAK CERTAIN FEATURES OF CRAFTY CONTROLLER")
		yn = input("If you wish to continue, type \"I understand, Break Crafty Controller management!\": ")
		if yn != 'I understand, Break Crafty Controller management!':
			print("Exiting")
			raise SystemExit
		print()
	if os.path.exists(f"{instance_dir}/../instance.cfg"):
		print("mcmodman has detected that this instance is managed by prism launcher\nwould you like to enable dual indexing for prism launcher compatibility?")
		prismcomp = input(":: Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			managefile += "\nindex-compatibility = \"prism\""
	if os.path.exists(f"{instance_dir}/../../profiles"):
		print("mcmodman has detected that this instance is managed by modrinth\n")

	with open(f"{instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
		f.write(managefile)
	if not os.path.exists(f"{instance_dir}/.content"):
		os.makedirs(f"{instance_dir}/.content")


if os.path.exists(os.path.expanduser("~/.config/ekno/mcmodman/config.toml")):
	config = toml.load(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"))
else:
	config = {"instances": [{"name": ".minecraft", "path": "~/.minecraft", "id": "0"}], "cache-dir": "autodetect", "include-beta": False, "api-expire": 3600, "checksum": "Always"}
	os.makedirs(os.path.expanduser("~/.config/ekno/mcmodman"))
	toml.dump(config, open(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"), 'w',  encoding='utf-8'))
if config['cache-dir'] == "autodetect":
	cachedir = os.path.expanduser("~/.cache/ekno/mcmodman")
elif config['cache-dir'] != "autodetect":
	cachedir = os.path.expanduser(config['cache-dir'])
if not os.path.exists(cachedir):
	os.makedirs(cachedir)
	os.makedirs(f"{cachedir}/mods")
	os.makedirs(f"{cachedir}/modrinth-api")
for instance in config['instances']: # TODO: add a way to change which instance is selected
	if instance["id"] == config["selected-instance"]:
		instance_dir = os.path.expanduser(instance["path"])
		break
else:
	print("selected instance not found")
	raise SystemExit
if not os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
	instance_firstrun()
if os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
	instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]
else:
	mod_loader = ""
	minecraft_version = ""
