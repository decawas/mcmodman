"""
Instance management functions for mcmodman
"""
from pathlib import Path
import os, re, json, logging, appdirs, requests
from configobj import ConfigObj
import commons, cache

logger = logging.getLogger(__name__)

def instanceFirstrun():
	instance = ConfigObj(unrepr=True)
	if os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "options.txt"))):
		instance["type"] = "client"
		instance["modfolder"] = "mods"
		with open(os.path.expanduser(os.path.join(commons.instance_dir, "logs", "latest.log")), "r", encoding="utf-8") as f:
			log = f.read()
		instance["loader"], instance["version"] = loaderdetect(log)
	elif os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "server.properties"))):
		instance["type"] = "server"
		with open(os.path.expanduser(os.path.join(commons.instance_dir, "logs", "latest.log")), "r", encoding="utf-8") as f:
			log = f.read()
		instance["loader"], instance["version"] = loaderdetect(log)
		instance["modfolder"] = "plugins" if instance["loader"] in ["folia", "purpur", "paper", "spigot", "bukkit"] else "mods"
	elif os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "level.dat"))):
		instance["type"] = "world"
		instance["loader"] = "datapack"
		instance["modfolder"] = "datapacks"
		cacheData = cache.getAPICache("versiondata.ini", "./")
		if cacheData:
			versionData = cacheData["api"]
		else:
			response = requests.get("https://raw.githubusercontent.com/PrismarineJS/minecraft-data/refs/heads/master/data/pc/common/protocolVersions.json", timeout=30)
			response.raise_for_status()
			versionData = response.json()
			cache.setAPICache("versiondata.ini", versionData, "./")
		advancements = sorted(Path(os.path.expanduser(os.path.join(commons.instance_dir, "advancements"))).iterdir(), key=os.path.getmtime)
		with open(os.path.expanduser(advancements[-1]), "r", encoding="utf-8") as f:
			advancements = json.loads(f.read())
		if "DataVersion" not in advancements or advancements["DataVersion"] < 1444:
			print("This world is too old, please upgrade to a more recent version to use datapacks")
			logger.warning("This world is too old, please upgrade to a more recent version to use datapacks")
			raise SystemExit
		for version in versionData:
			if version["dataVersion"] == advancements["DataVersion"]:
				instance["version"] = version["minecraftVersion"]
				break
	else:
		print("error: selected instance does not appear to be a minecraft instance")
	if instance["type"] != "world" and not os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "logs", "latest.log"))):
		print("instance must be run at least once before using mcmodman")
	
	instance["index-compatibility"] = compdetect(commons.instance_dir)
	
	instance.filename = os.path.join(commons.instance_dir, "mcmodman_managed.ini")
	instance.write()
	return instance

def loaderdetect(log):
	if os.path.exists(os.path.join(commons.instance_dir, "config", "quilt-loader.txt")):
		loader = "quilt"
		versionmatch = r"Minecraft (\d+(?:\.\d+)*) with"
	elif os.path.exists(os.path.join(commons.instance_dir, ".fabric")):
		loader = "fabric"
		versionmatch = r"Minecraft (\d+(?:\.\d+)*) with"
	elif os.path.exists(os.path.join(commons.instance_dir, "config", "sponge")):
		loader = "sponge"
		versionmatch = r"spongevanilla-(\d+(?:\.\d+)*)-"
	elif os.path.exists(os.path.join(commons.instance_dir, "config", "neoforge-client.toml")) or os.path.exists(os.path.join(commons.instance_dir, "config", "neoforge-server.toml")):
		loader = "neoforge"
		versionmatch = r"--version, (\d+(?:\.\d+)*),"
	elif os.path.exists(os.path.join(commons.instance_dir, "config", "forge-client.toml")) or os.path.exists(os.path.join(commons.instance_dir, "config", "forge-server.toml")):
		loader = "forge"
		versionmatch = r"--version, (\d+(?:\.\d+)*),"
	elif os.path.exists(os.path.join(commons.instance_dir, "config", "liteconfig")):
		loader = "liteloader"
		versionmatch = r"LiteLoader (\d+(?:\.\d+)*)\n"
	elif re.search(r"Purpur (\d+(?:\.\d+)*)-", str(log)) is not None:
		loader = "purpur"
		versionmatch = r"Purpur (\d+(?:\.\d+)*)-"
	elif re.search(r"Folia version (\d+(?:\.\d+)*)-", str(log)) is not None:
		loader = "folia"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	elif os.path.exists(os.path.join(commons.instance_dir, "config", "paper-global.yml")):
		loader = "paper"
		versionmatch = r"Paper (\d+(?:\.\d+)*)-"
	elif os.path.exists(os.path.join(commons.instance_dir, "spigot.yml")):
		loader = "spigot"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	elif os.path.exists(os.path.join(commons.instance_dir, "bukkit.yml")):
		loader = "bukkit"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	else:
		print("Could not detect loader automatically")
		raise SystemExit

	match = re.search(versionmatch, log)
	version = f"{match.group(1)}"
	return loader, version

def compdetect(instanceDir) -> str:
	"""Detect compatibility with launchers like MultiMC, PolyMC, etc."""
	if os.path.exists(f"{instanceDir}/../instance.cfg"):
		p = "Prism Launcher" if os.path.exists(f"{instanceDir}/../../../prismlauncher.cfg") else "PolyMC" if os.path.exists(f"{instanceDir}/../../../polymc.cfg") else "MultiMC"
		print(f"mcmodman has detected that this instance is managed by {p}\nwould you like to enable dual indexing for {p} compatibility?")
		logger.info("found instance.cfg, instance is likely managed by a MultiMC fork")
		prismcomp = input(f"{commons.color.INPUT}::{commons.color.NORMAL} Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			return "packwiz"

	return "None"

def instanceMeta():
	"""Handle instance management operations (add, select, remove, list)."""
	if commons.args["suboperation"] not in ["add", "select", "remove", "list"]:
		print("Usage: mcmodman --instance <add|select|remove|list>")
		logger.error("--intsance flag missing arguments")
		return
	if commons.args["suboperation"] == "add":
		if commons.args["name"] is None or commons.args["path"] is None:
			print("Usage: mcmodman --instance add <name> <path>")
			logger.error("--intsance flag missing arguments")
			return
		if commons.args["name"] in commons.instances.keys():
			print(f"Instance '{commons.args['name']}' already exists")
			return

		commons.instances[commons.args["name"]] = {"name": commons.args["name"], "path": commons.args["path"]}
		commons.instances.write()
		print(f"Added instance '{commons.args['name']}'")
	if commons.args["suboperation"] == "select":
		if commons.args["name"] in commons.instances:
			commons.config["selected-instance"] = commons.args["name"]
			commons.config.write()
			print(f"Selected instance '{commons.args['name']}'")
			return
		print(f"Instance '{commons.args['name']}' not found")
	if commons.args["suboperation"] == "remove":
		if commons.args["name"] == commons.config["selected-instance"]:
			print("cant delete selected instance")
			return
		for i, instance in enumerate(commons.config["instances"]):
			if instance["name"] == commons.args["name"]:
				del commons.config["instances"][i]
				commons.instances.write()
				print(f"Deleted instance '{commons.args['name']}'")
				return
		print(f"Instance '{commons.args['name']}' not found")
	if commons.args["suboperation"] == "list":
		for name in list(commons.instances.keys()):
			print(name, "*" if name == commons.config["selected-instance"] else "")
