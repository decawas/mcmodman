"""
Instance management functions for mcmodman
"""
from pathlib import Path
import os, re, json, logging, appdirs, requests
from configobj import ConfigObj
import cache

logger = logging.getLogger(__name__)

def instanceFirstrun(ctx):
	instance = ConfigObj(unrepr=True)
	if os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, "options.txt"))):
		instance["type"] = "client"
		instance["modfolder"] = "mods"
		with open(os.path.expanduser(os.path.join(ctx.instanceDir, "logs", "latest.log")), "r", encoding="utf-8") as f:
			log = f.read()
		instance["loader"], instance["version"] = loaderdetect(ctx, log)
	elif os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, "server.properties"))):
		instance["type"] = "server"
		with open(os.path.expanduser(os.path.join(ctx.instanceDir, "logs", "latest.log")), "r", encoding="utf-8") as f:
			log = f.read()
		instance["loader"], instance["version"] = loaderdetect(ctx, log)
		instance["modfolder"] = "plugins" if instance["loader"] in ["folia", "purpur", "paper", "spigot", "bukkit"] else "mods"
	elif os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, "level.dat"))):
		instance["type"] = "world"
		instance["loader"] = "datapack"
		instance["modfolder"] = "datapacks"
		cacheData = cache.getAPICache(ctx, "versiondata.ini", "./")
		if cacheData:
			versionData = cacheData["api"]
		else:
			response = requests.get("https://raw.githubusercontent.com/PrismarineJS/minecraft-data/refs/heads/master/data/pc/common/protocolVersions.json", timeout=30)
			response.raise_for_status()
			versionData = response.json()
			cache.setAPICache(ctx, "versiondata.ini", versionData, "./")
		advancements = sorted(Path(os.path.expanduser(os.path.join(ctx.instanceDir, "advancements"))).iterdir(), key=os.path.getmtime)
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
	if instance["type"] != "world" and not os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, "logs", "latest.log"))):
		print("instance must be run at least once before using mcmodman")
	
	instance["index-compatibility"] = compdetect(ctx.instanceDir)
	
	instance.filename = os.path.join(ctx.instanceDir, "mcmodman_managed.ini")
	instance.write()
	return instance

def loaderdetect(ctx, log):
	if os.path.exists(os.path.join(ctx.instanceDir, "config", "quilt-loader.txt")):
		loader = "quilt"
		versionmatch = r"Minecraft (\d+(?:\.\d+)*) with"
	elif os.path.exists(os.path.join(ctx.instanceDir, ".fabric")):
		loader = "fabric"
		versionmatch = r"Minecraft (\d+(?:\.\d+)*) with"
	elif os.path.exists(os.path.join(ctx.instanceDir, "config", "sponge")):
		loader = "sponge"
		versionmatch = r"spongevanilla-(\d+(?:\.\d+)*)-"
	elif os.path.exists(os.path.join(ctx.instanceDir, "config", "neoforge-client.toml")) or os.path.exists(os.path.join(ctx.instanceDir, "config", "neoforge-server.toml")):
		loader = "neoforge"
		versionmatch = r"--version, (\d+(?:\.\d+)*),"
	elif os.path.exists(os.path.join(ctx.instanceDir, "config", "forge-client.toml")) or os.path.exists(os.path.join(ctx.instanceDir, "config", "forge-server.toml")):
		loader = "forge"
		versionmatch = r"--version, (\d+(?:\.\d+)*),"
	elif os.path.exists(os.path.join(ctx.instanceDir, "config", "liteconfig")):
		loader = "liteloader"
		versionmatch = r"LiteLoader (\d+(?:\.\d+)*)\n"
	elif re.search(r"Purpur (\d+(?:\.\d+)*)-", str(log)) is not None:
		loader = "purpur"
		versionmatch = r"Purpur (\d+(?:\.\d+)*)-"
	elif re.search(r"Folia version (\d+(?:\.\d+)*)-", str(log)) is not None:
		loader = "folia"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	elif os.path.exists(os.path.join(ctx.instanceDir, "config", "paper-global.yml")):
		loader = "paper"
		versionmatch = r"Paper (\d+(?:\.\d+)*)-"
	elif os.path.exists(os.path.join(ctx.instanceDir, "spigot.yml")):
		loader = "spigot"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	elif os.path.exists(os.path.join(ctx.instanceDir, "bukkit.yml")):
		loader = "bukkit"
		versionmatch = r"server version (\d+(?:\.\d+)*)\n"
	else:
		print("Could not detect loader automatically")
		raise SystemExit

	match = re.search(versionmatch, log)
	version = f"{match.group(1)}"
	return loader, version

def compdetect(ctx) -> str:
	"""Detect compatibility with launchers like MultiMC, PolyMC, etc."""
	if os.path.exists(f"{ctx.instanceDir}/../instance.cfg"):
		p = "Prism Launcher" if os.path.exists(f"{ctx.instanceDir}/../../../prismlauncher.cfg") else "PolyMC" if os.path.exists(f"{ctx.instanceDir}/../../../polymc.cfg") else "MultiMC"
		print(f"mcmodman has detected that this instance is managed by {p}\nwould you like to enable dual indexing for {p} compatibility?")
		logger.info("found instance.cfg, instance is likely managed by a MultiMC fork")
		prismcomp = input(f"{ctx.color.INPUT}::{ctx.color.NORMAL} Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			return "packwiz"

	return "None"

def instanceMeta(ctx):
	"""Handle instance management operations (add, select, remove, list)."""
	if ctx.args["suboperation"] not in ["add", "select", "remove", "list"]:
		print("Usage: mcmodman --instance <add|select|remove|list>")
		logger.error("--intsance flag missing arguments")
		return
	if ctx.args["suboperation"] == "add":
		if ctx.args["name"] is None or ctx.args["path"] is None:
			print("Usage: mcmodman --instance add <name> <path>")
			logger.error("--intsance flag missing arguments")
			return
		if ctx.args["name"] in ctx.instance.keys():
			print(f"Instance '{ctx.args['name']}' already exists")
			return

		ctx.instance[ctx.args["name"]] = {"name": ctx.args["name"], "path": ctx.args["path"]}
		ctx.instance.write()
		print(f"Added instance '{ctx.args['name']}'")
	if ctx.args["suboperation"] == "select":
		if ctx.args["name"] in ctx.instance:
			ctx.config["selected-instance"] = ctx.args["name"]
			ctx.config.write()
			print(f"Selected instance '{ctx.args['name']}'")
			return
		print(f"Instance '{ctx.args['name']}' not found")
	if ctx.args["suboperation"] == "remove":
		if ctx.args["name"] == ctx.config["selected-instance"]:
			print("cant delete selected instance")
			return
		for i, instance in enumerate(ctx.config["instances"]):
			if instance["name"] == ctx.args["name"]:
				del ctx.config["instances"][i]
				ctx.instance.write()
				print(f"Deleted instance '{ctx.args['name']}'")
				return
		print(f"Instance '{ctx.args['name']}' not found")
	if ctx.args["suboperation"] == "list":
		for name in list(ctx.instance.keys()):
			print(name, "*" if name == ctx.config["selected-instance"] else "")
