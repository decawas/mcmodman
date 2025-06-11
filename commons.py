"""
defines common variables, and meta-instance functions
"""
import argparse
import logging, os, sys, appdirs, tomlkit
from configobj import ConfigObj, validate
from instance import instanceFirstrun

__version__ = "25.21"
logger = logging.getLogger(__name__)

def parse_args():
	parser = argparse.ArgumentParser(description="mcmodman command line interface")
	ops = parser.add_mutually_exclusive_group(required=True)
	ops.add_argument("-S", "--sync", action="store_true", help="Sync mods")
	ops.add_argument("-U", "--upgrade", action="store_true", help="Upgrade mods")
	ops.add_argument("-R", "--remove", action="store_true", help="Remove mods")
	ops.add_argument("-T", "--toggle", action="store_true", help="Toggle mods")
	ops.add_argument("-Q", "--query", action="store_true", help="Query mods")
	ops.add_argument("-D", "--downgrade", action="store_true", help="Downgrade mods")
	ops.add_argument("--ignore", action="store_true", help="Ignore mods")
	ops.add_argument("-F", "--search", action="store_true", help="Search mods")
	ops.add_argument("--cc", nargs='?', const=True, metavar="SUBOPERATION", help="Clear cache")
	ops.add_argument("--instance", nargs="+", metavar=("SUBOPERATION", "NAME", "PATH"), help="Instance operations")
	ops.add_argument("--version", action="store_true")
	
	asexpldeps = parser.add_mutually_exclusive_group()
	asexpldeps.add_argument("--asexplicit", action="store_true", help="Define newly installed mods as explicit, even if they are dependencies")
	asexpldeps.add_argument("--asdeps", action="store_true", help="Define newly installed mods as dependencies, even if they are installed explicitly")

	parser.add_argument("-a", "--all", action="store_true", help="Apply to all")
	parser.add_argument("-e", "--explicit", action="store_true", help="Explicit")
	parser.add_argument("-d", "--dependency", action="store_true", help="Dependency")
	parser.add_argument("-p", "--optional", action="store_true", help="Optional")
	parser.add_argument("-y", "--noconfirm", action="store_true", help="Skip the confirmation dialogue, does not skip the ignore question in downgrade")
	parser.add_argument("-c", "--color", action="store_true", help="Enable colour output")
	parser.add_argument("slugs", nargs="*", help="Mod slugs to operate on")

	try:
		args = parser.parse_args()
	except TypeError:
		print("error: no operation specified")
		logger.critical("no operation")
		raise SystemExit
	result = {}
	if args.sync:
		result["operation"] = "sync"
		result["slugs"] = args.slugs
	elif args.upgrade:
		result["operation"] = "upgrade"
		result["slugs"] = args.slugs
	elif args.remove:
		result["operation"] = "remove"
		result["slugs"] = args.slugs
	elif args.toggle:
		result["operation"] = "toggle"
		result["slugs"] = args.slugs
	elif args.query:
		result["operation"] = "query"
		result["slugs"] = args.slugs
	elif args.downgrade:
		result["operation"] = "downgrade"
		result["slugs"] = args.slugs
	elif args.ignore:
		result["operation"] = "ignore"
		result["slugs"] = args.slugs
	elif args.search:
		result["operation"] = "search"
		result["query"] = " ".join(args.slugs)
	elif args.version:
		result["operation"] = "version"
	elif args.cc:
		result["operation"] = "clear-cache"
		result["suboperation"] = args.cc or ""
	elif args.instance:
		result["operation"] = "instance"
		result["suboperation"] = args.instance[0]
		result["name"] = args.instance[1] if len(args.instance) > 1 else None
		result["path"] = args.instance[2] if len(args.instance) > 2 else None

	result["all"] = args.all
	result["explicit"] = args.explicit
	result["dependency"] = args.dependency
	result["optional"] = args.optional
	result["noconfirm"] = args.noconfirm
	result["color"] = args.color
	result["asexplicit"] = args.asexplicit
	result["asdeps"] = args.asdeps
	result["lock"] = result.get("operation") in ["sync", "update", "remove", "toggle", "downgrade"]
	return result

class InvalidOption(Exception):
	"error: invalid option"

config_dir = appdirs.user_config_dir("ekno/mcmodman")
exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)) 

if not os.path.exists(config_dir):
	os.makedirs(config_dir)

config_file = os.getenv("MCMMCONFIG", os.path.expanduser(os.path.join(config_dir, "mcmodman.conf")))
if os.path.exists(os.path.join(config_dir, "config.toml")) and not os.path.exists(config_file):
	with open(os.path.join(config_dir, "config.toml"), "r") as f:
		oldconfig = tomlkit.load(f)
	config = ConfigObj(unrepr=True)
	config.filename = config_file
	for value in oldconfig:
		config[value] = oldconfig[value]
	config.write()
	os.remove(os.path.join(config_dir, "config.toml"))
elif not os.path.exists(config_file):
	if not os.path.exists(os.path.join(exe_dir, "config-template.ini")):
		raise FileNotFoundError
	config = ConfigObj(os.path.join(exe_dir, "config-template.ini"), unrepr=True)
	config["cache-dir"] = appdirs.user_cache_dir("ekno/mcmodman")
	config["log-file"] = os.path.join(config_dir, "mcmodman.log")
	config.filename = config_file
	config.write()
else:
	config = ConfigObj(config_file, unrepr=True)

logger.info(config)

logging.basicConfig(filename=config["log-file"], level=logging.NOTSET)
logger.info("Starting mcmodman version %s", __version__)

logger.info("Config directory: %s", config_dir)

try:
	args = parse_args()
	logger.info("Arguments: %s", args)
except Exception as e:
	print("error: invalid option")
	logger.critical("invalid option")
	raise

instances_file = config.get("instances-file", os.path.join(config_dir, "instances.ini"))
if os.path.exists(os.path.join(config_dir, "instances.toml")) and not os.path.exists(instances_file):
	with open(os.path.join(config_dir, "instances.toml"), "r") as f:
		oldinstances = tomlkit.load(f)
	instances = ConfigObj(unrepr=True)
	instances.filename = instances_file
	for value in oldinstances:
		instances[value] = oldinstances[value]
	instances.write()
	os.remove(os.path.join(config_dir, "instances.toml"))
elif not os.path.exists(instances_file):
	instances = ConfigObj(unrepr=True)
	instances["dotminecraft"] = {"name": ".minecraft", "path": "~/%AppData%/roaming/.minecraft" if "win" in sys.platform else "~/Library/Application Support/minecraft" if "darwin" in sys.platform else "~/.minecraft"}
	instances.filename = instances_file
	instances.write()
else:
	instances = ConfigObj(instances_file, unrepr=True)
logger.info("instances %s", instances)

cacheDir = config["cache-dir"]
logger.info("Cache directory: %s", cacheDir)
if not os.path.exists(cacheDir):
	os.makedirs(cacheDir)
	os.makedirs(os.path.join(cacheDir, "mods"))

class color:
	NORMAL = "\033[0m"
	INPUT = "\033[94m" if args["color"] or config.get("Color", False) else "\033[0m"
	ERROR = "\033[91m" if args["color"] or config.get("Color", False) else "\033[0m"

if args["operation"] != "instance":
	selected_instance = os.getenv("MCMMINSTANCE", config["selected-instance"])
	if selected_instance in instances:
		instance_dir = os.path.expanduser(instances[selected_instance]["path"])
	else:
		print("selected instance not found")
		raise SystemExit
	logger.info("selected instance: %s", selected_instance)

	if not os.path.exists(os.path.join(instance_dir, "mcmodman_managed.ini")):
		instanceFirstrun(instance_dir)

	instancecfg = ConfigObj(os.path.join(instance_dir, "mcmodman_managed.ini"))
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]

	logger.info("instance %s", instancecfg)

	loaderUpstreams = {"quilt": ["fabric"], "neoforge": ["forge"], "folia": ["paper","spigot","bukkit"], "purpur": ["paper","spigot","bukkit"], "paper": ["spigot","bukkit"], "spigot": ["bukkit"]}