"""
defines common variables, and meta-instance functions
"""
from sys import argv
import logging, os, appdirs, toml
from instance import instanceFirstrun

__version__ = "25.3+"
logger = logging.getLogger(__name__)

def argparse():
	args = {}
	if "mcmodman" in argv[0]:
		del argv[0]
	if not argv:
		print("No operation specified")
		logger.warning("No operation specified")
		raise SystemExit

	if argv[0][:2] == "-S":
		args["operation"] = "sync"
	elif argv[0][:2] == "-U":
		args["operation"] = "update"
	elif argv[0][:2] == "-R":
		args["operation"] = "remove"
	elif argv[0] == "-T":
		args["operation"] = "toggle"
	elif argv[0][:2] == "-Q":
		args["operation"] = "query"
	elif argv[0][:2] == "-D":
		args["operation"] = "downgrade"
	elif argv[0] == "-F":
		args["operation"] = "search"
	elif argv[0] == "--cc":
		args["operation"] = "clear-cache"
	elif argv[0] == "--instance":
		args["operation"] = "instance"
	else:
		raise InvalidOption("error: invalid option")

	if argv[0][1] in ("S", "U", "R", "T", "Q", "D"):
		args["slugs"] = argv[1:]
	elif argv[0][1] == "F":
		args["query"] = " ".join(argv[1:])
	elif argv[0] in ["--instance", "--cc"]:
		args["suboperation"] = argv[1]
		args["name"] = None if len(argv) < 3 else argv[2]
		args["path"] = None if len(argv) < 4 else argv[3]
	args["all"] = "a" in argv[0]
	args["explicit"] = "e" in argv[0]
	args["depedency"] = "d" in argv[0]
	args["optional"] = "p" in argv[0]
	args["auto-confirm"] = "y" in argv[0]
	args["lock"] = argv[0][1] in ["S", "U", "R", "T", "D"]

	return args

class InvalidOption(Exception):
	"error: invalid option"

config_dir = appdirs.user_config_dir("ekno/mcmodman")

if not os.path.exists(config_dir):
	os.makedirs(config_dir)

if not os.path.exists(os.path.expanduser(os.path.join(config_dir, "config.toml"))):
	with open(os.path.expanduser(os.path.join(config_dir, "config.toml")), "w", encoding="utf-8") as f:
		config = toml.load("config-template.toml")
		config["cache-dir"] = appdirs.user_cache_dir("ekno/mcmodman")
		config["log-file"] = os.path.join(config_dir, "mcmodman.log")
		toml.dump(config, f)
else:
	config = toml.load(os.path.join(config_dir, "config.toml"))

logging.basicConfig(filename=config["log-file"], level=logging.NOTSET)
logger.info("Starting mcmodman version %s", __version__)

logger.info("Config directory: %s", config_dir)

try:
	args = argparse()
	logger.info("Arguments: %s", args)
except InvalidOption as e:
	print("error: invalid option")
	logger.critical("invalid option")
	raise SystemExit from e

if not os.path.exists(os.path.join(config_dir, "instances.toml")):
	with open(os.path.join(config_dir, "instances.toml"), 'w',  encoding='utf-8') as f:
		instances = {"dotminecraft": {"name": ".minecraft", "path": "~/.minecraft"}}
		toml.dump(instances, f)
else:
	instances = toml.load(os.path.join(config_dir, "instances.toml"))
logger.info("instances %s", instances)

if "--instance" not in argv:
	cacheDir = config["cache-dir"]
	logger.info("Cache directory: %s", cacheDir)
	if not os.path.exists(cacheDir):
		os.makedirs(cacheDir)
		os.makedirs(os.path.join(cacheDir, "mods"))
		os.makedirs(os.path.join(cacheDir, "modrinth-api"))

	selected_instance = config["selected-instance"]
	if selected_instance in instances.keys():
		instance_dir = os.path.expanduser(instances[selected_instance]["path"])
	else:
		print("selected instance not found")
		raise SystemExit

	if not os.path.exists(os.path.join(instance_dir, "mcmodman_managed.toml")):
		instanceFirstrun(instance_dir)

	instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]

	logger.info("instance %s", instancecfg)

	loaderUpstreams = {"quilt": ["fabric"], "neoforge": ["forge"], "folia": ["paper","spigot","bukkit"], "purpur": ["paper","spigot","bukkit"], "paper": ["spigot","bukkit"], "spigot": ["bukkit"]}
