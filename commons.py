# pylint: disable=C0114 C0116 C0410 E0606 E0401
# pylint: disable=W0621
from argparse import ArgumentParser, SUPPRESS
import logging, re, os, appdirs, toml

__version__ = "25.3"

def instance_firstrun():
	if os.path.exists(os.path.expanduser(f"{instance_dir}/logs/latest.log")):
		with open(os.path.expanduser(f"{instance_dir}/logs/latest.log"), "r", encoding="utf-8") as f:
			log = f.read()
	else:
		print("instance must be run at least once before using mcmodman")
		raise SystemExit

	loaders = []
	loader_detector = {"quilt": {"detect": lambda: os.path.exists(f"{instance_dir}/config/quilt-loader.txt"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
    "neoforge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/neoforge-client.toml") or os.path.exists(f"{instance_dir}/config/neoforge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
    "fabric": {"detect": lambda: os.path.exists(f"{instance_dir}/.fabric"), "version_detect": r"Minecraft (\d+(?:\.\d+)*) with"},
    "forge": {"detect": lambda: os.path.exists(f"{instance_dir}/config/forge-client.toml") or os.path.exists(f"{instance_dir}/config/forge-server.toml"), "version_detect": r"--version, (\d+(?:\.\d+)*),"},
    "liteloader": {"detect": lambda: os.path.exists(f"{instance_dir}/config/liteconfig"), "version_detect": r"LiteLoader (\d+(?:\.\d+)*)\n"},
    "purpur": {"detect": lambda: re.search(r"Purpur (\d+(?:\.\d+)*)-", log) is not None, "version_detect": r"Purpur (\d+(?:\.\d+)*)-"},
    "folia": {"detect": lambda: re.search(r"Folia version (\d+(?:\.\d+)*)-", log) is not None, "version_detect": r"server version (\d+(?:\.\d+)*)\n"},
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

	if len(loaders) > 1:
		if loaders[0] not in ["folia", "purper", "paper", "spigot"]:
			print("mcmodman does not support instances with multiple loaders")
			raise RuntimeError("mcmodman does not support instances with multiple loaders")
	if not loaders:
		print("Could not find any mod loaders for this instance\nif you are using Rift, RML or have no mod loader you will have to manually set that")
		raise RuntimeError("mcmodman could not find any loaders for this instance")
	managefile = {"loader": loaders[0]}

	managefile["modfolder"] = "plugins" if re.search(loaders[0], "purpur,folia,paper,spigot,bukkit") is not None else "mods"

	if match:
		managefile["version"] = f"{match.group(1)}"
	else:
		raise RuntimeError("mcmodman could not find a minecraft version")

	comp = compdetect()
	if comp is not None:
		managefile["index-compatibity"] = comp

	with open(f"{instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
		toml.dump(managefile, f)
		logger.info("writing mcmodman_managed.toml to instance")
	if not os.path.exists(f"{instance_dir}/.content"):
		os.makedirs(f"{instance_dir}/.content")

def compdetect():
	if os.path.exists(f"{instance_dir}/../instance.cfg"):
		if os.path.exists(f"{instance_dir}/../../../prismlauncher.cfg"):
			print("mcmodman has detected that this instance is managed by prism launcher\nwould you like to enable dual indexing for prism launcher compatibility?")
			logger.info("found instance.cfg and prismlauncher.cfg, instance is likely managed by Prism Launcher")
		if os.path.exists(f"{instance_dir}/../../../polymc.cfg"):
			print("mcmodman has detected that this instance is managed by poly mc\nwould you like to enable dual indexing for poly mc compatibility?")
			logger.info("found instance.cfg and ploymc.cfg, instance is likely managed by PolyMC")
		prismcomp = input(":: Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			return "packwiz"

	return None

def add_instance():
	name = input(":: Enter instance name: ")
	path = input(":: Enter instance path: ")
	if name in instances.keys():
		print(f"Instance '{name}' already exists")
		return "instance"

	instances[name] = {"name": name, "path": path}
	with open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8') as f:
		toml.dump(instances, f)
	print(f"Added instance '{name}'")

def sel_instance():
	name = input(":: Enter instance name: ")
	if name in instances:
		config["selected-instance"] = name
		with open(f"{config_dir}/config.toml", 'w',  encoding='utf-8') as f:
			toml.dump(config, f)
		print(f"Selected instance '{name}'")
		return "instance"
	print(f"Instance '{name}' not found")
	return "no instance"

def del_instance():
	name = input(":: Enter instance name: ")
	if name == config["selected-instance"]:
		print("cant delete selected instance")
		return "instance"
	for i, instance in enumerate(config["instances"]):
		if instance["name"] == name:
			del config["instances"][i]
			with open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8') as f:
				toml.dump(instances, f)
			print(f"Deleted instance '{name}'")
			return "instance"
	print(f"Instance '{name}' not found")
	return "no instance"


parser = ArgumentParser(description='mcmodman')
parser.add_argument('-S', nargs='+', type=str, help='-S [mod_slug]', dest="addbyslug", default=SUPPRESS)
parser.add_argument('-U', nargs='+', type=str, help='-U [mod_slug]', dest="update", default=SUPPRESS)
parser.add_argument('-R', nargs='+', type=str, help='-R [mod_slug]', dest="remove", default=SUPPRESS)
parser.add_argument('-Q', nargs='*', type=str, help='-Q [mod_slug]', dest="query", default=SUPPRESS)
parser.add_argument('-T', nargs='+', type=str, help='-T [mod_slug]', dest="toggle", default=SUPPRESS)
parser.add_argument('-F', nargs='+', type=str, help='-F [search query]', dest="search", default=SUPPRESS)
parser.add_argument('-D', nargs='+', type=str, help='-D [mod_slug]', dest="downgrade", default=SUPPRESS)
parser.add_argument('-cc', nargs='?', const=True, type=str, help='clear cache, -cc expired|api|all', default=SUPPRESS)
parser.add_argument('--instance', nargs='?', const=True, type=str, help='instance add|select|remove', default=SUPPRESS)
parser.add_argument('--version', action="store_true", help='-version', default=SUPPRESS)
args=parser.parse_args()

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

if "instance" not in args:
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
