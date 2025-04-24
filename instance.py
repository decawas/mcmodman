"""
Instance management functions for mcmodman
"""
from pathlib import Path
import os, re, json, logging, toml, appdirs
import commons

# Global variables
config_dir = appdirs.user_config_dir("ekno/mcmodman")
logger = logging.getLogger(__name__)

def instanceFirstrun(instance_dir):
	"""Initialize a new instance with the necessary configuration."""
	managefile = {}
	if os.path.exists(os.path.expanduser(f"{instance_dir}/logs/latest.log")):
		with open(os.path.expanduser(f"{instance_dir}/logs/latest.log"), "r", encoding="utf-8") as f:
			log = f.read()
		loaders = []
		loader_detector = {
			"quilt": {"detect": lambda: os.path.exists(f"{instance_dir}/config/quilt-loader.txt"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
			"neoforge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/neoforge-client.toml") or os.path.exists(f"{instance_dir}/config/neoforge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
			"fabric": {"detect": lambda: os.path.exists(f"{instance_dir}/.fabric"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
			"forge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/forge-client.toml") or os.path.exists(f"{instance_dir}/config/forge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
			"liteloader": {"detect": lambda: os.path.exists(f"{instance_dir}/config/liteconfig"), "version_detect": r"LiteLoader (\d+(?:\.\d+)*)\n"},
			"purpur": {"detect": lambda: re.search(r"Purpur (\d+(?:\.\d+)*)-", str(log)) is not None, "version_detect": r"Purpur (\d+(?:\.\d+)*)-"},
			"folia": {"detect": lambda: re.search(r"Folia version (\d+(?:\.\d+)*)-", str(log)) is not None, "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
			"paper": {"detect": lambda: os.path.exists(f"{instance_dir}/config/paper-global.yml"), "version_detect": r"Paper (\d+(?:\.\d+)*)-"},
			"spigot": {"detect": lambda: os.path.exists(f"{instance_dir}/spigot.yml"), "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
			"bukkit": {"detect": lambda: os.path.exists(f"{instance_dir}/bukkit.yml"), "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
			"sponge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/sponge/sponge.conf"), "version_detect": r"spongevanilla-(\d+(?:\.\d+)*)-"}
		}

		logger.info("Found loaders %s", ", ".join(loaders))
		for loader, det in loader_detector.items():
			if det["detect"]():
				loaders.append(loader)
				match = re.search(det["version_detect"], log)
				break
		managefile["modfolder"] = "plugins" if re.search(loaders[0], "purpur,folia,paper,spigot,bukkit") is not None else "mods"

		managefile["index-compatibity"] = compdetect(instance_dir)
	elif os.path.exists(os.path.expanduser(f"{instance_dir}/level.dat")):
		advancements = sorted(Path(os.path.expanduser(f"{instance_dir}/advancements")).iterdir(), key=os.path.getmtime)
		with open(os.path.expanduser(advancements[-1]), "r", encoding="utf-8") as f:
			log = json.loads(f.read())
		with open("dataversion.json", "r", encoding="utf-8") as f:
			dataversions = json.loads(f.read())

		if "DataVersion" not in log or log["DataVersion"] < 1444:
			print("This world is too old, please upgrade to a more recent version to use datapacks")
			logger.warning("This world is too old, please upgrade to a more recent version to use datapacks")
			raise SystemExit

		loaders = ["datapack"]
		match = dataversions[0][str(log["DataVersion"])]
		managefile["modfolder"] = "datapacks"
	else:
		print("instance must be run at least once before using mcmodman")
		raise SystemExit

	if len(loaders) > 1 and loaders[0] not in ["folia", "purper", "paper", "spigot"]:
		print("mcmodman does not support instances with multiple loaders")
		raise RuntimeError("mcmodman does not support instances with multiple loaders")
	if not loaders:
		print("Could not find any mod loaders for this instance\nif you are using Rift or RML you will have to manually set that")
		loaders = ["vanilla"]

	managefile["loader"] = loaders[0]

	managefile["type"] = "server" if os.path.exists(f"{instance_dir}/server.properties") else "client" if os.path.exists(f"{instance_dir}/options.txt") else "world" if os.path.exists(f"{instance_dir}/level.dat") else None
	if managefile["type"] is None:
		print("Could not determine instance type")
		raise RuntimeError("Could not determine instance type")

	if match:
		managefile["version"] = f"{match.group(1)}" if not isinstance(match, str) else match
	else:
		raise RuntimeError("mcmodman could not find a minecraft version")

	with open(f"{instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
		toml.dump(managefile, f)
		logger.info("writing mcmodman_managed.toml to instance")

	os.makedirs(f"{instance_dir}/.content")
	return managefile

def compdetect(instanceDir):
	"""Detect compatibility with launchers like MultiMC, PolyMC, etc."""
	if os.path.exists(f"{instanceDir}/../instance.cfg"):
		p = "Prism Launcher" if os.path.exists(f"{instanceDir}/../../../prismlauncher.cfg") else "PolyMC" if os.path.exists(f"{instanceDir}/../../../polymc.cfg") else "MultiMC"
		print(f"mcmodman has detected that this instance is managed by {p}\nwould you like to enable dual indexing for {p} compatibility?")
		logger.info("found instance.cfg, instance is likely managed by a MultiMC fork")
		prismcomp = input(":: Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			return "packwiz"

	return None

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
		with open(f"{config_dir}/instances.toml", 'w', encoding='utf-8') as f:
			toml.dump(commons.instances, f)
		print(f"Added instance '{commons.args['name']}'")
	if commons.args["suboperation"] == "select":
		if commons.args["name"] in commons.instances:
			commons.config["selected-instance"] = commons.args["name"]
			with open(f"{config_dir}/config.toml", 'w', encoding='utf-8') as f:
				toml.dump(commons.config, f)
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
				with open(f"{config_dir}/instances.toml", 'w', encoding='utf-8') as f:
					toml.dump(commons.instances, f)
				print(f"Deleted instance '{commons.args['name']}'")
				return
		print(f"Instance '{commons.args['name']}' not found")
	if commons.args["suboperation"] == "list":
		for name in list(commons.instances.keys()):
			print(name, "*" if name == commons.config["selected-instance"] else "")
