# pylint: disable=C0116 C0410 W0621
"""
defines common variables, and meta-instance functions
"""
from sys import argv
import logging, re, os, json, appdirs, toml

__version__ = "25.3+"

def instance_firstrun():
	managefile = {}
	if os.path.exists(os.path.expanduser(f"{instance_dir}/logs/latest.log")):
		with open(os.path.expanduser(f"{instance_dir}/logs/latest.log"), "r", encoding="utf-8") as f:
			log = f.read()
		loaders = []
		loader_detector = {"quilt": {"detect": lambda: os.path.exists(f"{instance_dir}/config/quilt-loader.txt"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
		"neoforge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/neoforge-client.toml") or os.path.exists(f"{instance_dir}/config/neoforge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
		"fabric": {"detect": lambda: os.path.exists(f"{instance_dir}/.fabric"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
		"forge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/forge-client.toml") or os.path.exists(f"{instance_dir}/config/forge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
		"liteloader": {"detect": lambda: os.path.exists(f"{instance_dir}/config/liteconfig"), "version_detect": r"LiteLoader (\d+(?:\.\d+)*)\n"},
		"purpur": {"detect": lambda: re.search(r"Purpur (\d+(?:\.\d+)*)-", str(log)) is not None, "version_detect": r"Purpur (\d+(?:\.\d+)*)-"},
		"folia": {"detect": lambda: re.search(r"Folia version (\d+(?:\.\d+)*)-", str(log)) is not None, "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
		"paper": {"detect": lambda: os.path.exists(f"{instance_dir}/config/paper-global.yml"), "version_detect": r"Paper (\d+(?:\.\d+)*)-"},
		"spigot": {"detect": lambda: os.path.exists(f"{instance_dir}/spigot.yml"), "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
		"bukkit": {"detect": lambda: os.path.exists(f"{instance_dir}/bukkit.yml"), "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
		"sponge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/sponge/sponge.conf"), "version_detect": r"spongevanilla-(\d+(?:\.\d+)*)-"}}

		logger.info("Found loaders %s", ", ".join(loaders))
		for loader, det in loader_detector.items():
			if det["detect"]():
				loaders.append(loader)
				match = re.search(det["version_detect"], log)
				break
		managefile["modfolder"] = "plugins" if re.search(loaders[0], "purpur,folia,paper,spigot,bukkit") is not None else "mods"

		managefile["index-compatibity"] = compdetect()
	elif os.path.exists(os.path.expanduser(f"{instance_dir}/level.dat")):
		from pathlib import Path

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

def compdetect():
	if os.path.exists(f"{instance_dir}/../instance.cfg"):
		p = "Prism Launcher" if os.path.exists(f"{instance_dir}/../../../prismlauncher.cfg") else "PolyMC" if os.path.exists(f"{instance_dir}/../../../polymc.cfg") else "MultiMC"
		print(f"mcmodman has detected that this instance is managed by {p}\nwould you like to enable dual indexing for {p} compatibility?")
		logger.info("found instance.cfg, instance is likely managed by a MultiMC fork")
		prismcomp = input(":: Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			return "packwiz"

	return None

def instance_meta():
	if len(args) < 3:
		print("Usage: mcmodman --instance <add|select|remove>")
		logger.error("--intsance flag missing arguments")
		return
	name = args[2]
	if args[1] == "add":
		if len(args) < 4:
			print("Usage: mcmodman --instance add <name> <path>")
			logger.error("--intsance flag missing arguments")
		if name in instances.keys():
			print(f"Instance '{name}' already exists")
			return

		instances[name] = {"name": name, "path": args[3]}
		with open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8') as f:
			toml.dump(instances, f)
		print(f"Added instance '{name}'")
	if args[1] == "select":
		if name in instances:
			config["selected-instance"] = name
			with open(f"{config_dir}/config.toml", 'w',  encoding='utf-8') as f:
				toml.dump(config, f)
			print(f"Selected instance '{name}'")
			return
	print(f"Instance '{name}' not found")
	if args[1] == "remove":
		name = input(":: Enter instance name: ")
		if name == config["selected-instance"]:
			print("cant delete selected instance")
			return
		for i, instance in enumerate(config["instances"]):
			if instance["name"] == name:
				del config["instances"][i]
				with open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8') as f:
					toml.dump(instances, f)
				print(f"Deleted instance '{name}'")
				return
		print(f"Instance '{name}' not found")

args = argv
if args[0] == "mcmodman.py":
	del args[0]

config_dir = appdirs.user_config_dir("ekno/mcmodman")

logger = logging.getLogger(__name__)
logging.basicConfig(filename=f"{config_dir}/mcmodman.log", level=logging.NOTSET)
logger.info("Starting mcmodman version %s", __version__)
logger.info("Arguments: %s", args)

logger.info("Config directory: %s", config_dir)
if not os.path.exists(config_dir):
	os.makedirs(config_dir)

if os.path.exists(f"{config_dir}/config.toml"):
	config = toml.load(f"{config_dir}/config.toml")
else:
	with open(f"{config_dir}/config.toml", "w", encoding="utf-8") as f:
		config = {"include-beta": False, "api-expire": 3600, "checksum": "Always", "selected-instance": "dotminecraft"}
		toml.dump(config, f)

if not os.path.exists(f"{config_dir}/instances.toml"):
	with open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8') as f:
		instances = {"dotminecraft": {"name": ".minecraft", "path": "~/.minecraft"}}
		toml.dump(instances, f)
else:
	instances = toml.load(f"{config_dir}/instances.toml")
	logger.info("instances %s", instances)

if "--instance" not in args:
	cache_dir = appdirs.user_cache_dir("ekno/mcmodman")
	logger.info("Cache directory: %s", cache_dir)
	if not os.path.exists(cache_dir):
		os.makedirs(cache_dir)
		os.makedirs(f"{cache_dir}/mods")
		os.makedirs(f"{cache_dir}/modrinth-api")

	selected_instance = config["selected-instance"]
	if selected_instance in instances.keys():
		instance_dir = os.path.expanduser(instances[selected_instance]["path"])
	else:
		print("selected instance not found")
		raise SystemExit

	if not os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
		instance_firstrun()

	instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]

	logger.info("instance %s", instancecfg)
