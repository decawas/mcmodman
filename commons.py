"""
defines common variables, and meta-instance functions
"""
import argparse
import logging, os, sys, appdirs, toml
from instance import instanceFirstrun

__version__ = "25.21"
logger = logging.getLogger(__name__)

def parse_args():
	parser = argparse.ArgumentParser(description="mcmodman command line interface")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-S", "--sync", action="store_true", help="Sync mods")
	group.add_argument("-U", "--upgrade", action="store_true", help="Upgrade mods")
	group.add_argument("-R", "--remove", action="store_true", help="Remove mods")
	group.add_argument("-T", "--toggle", action="store_true", help="Toggle mods")
	group.add_argument("-Q", "--query", action="store_true", help="Query mods")
	group.add_argument("-D", "--downgrade", action="store_true", help="Downgrade mods")
	group.add_argument("--ignore", action="store_true", help="Ignore mods")
	group.add_argument("-F", "--search", action="store_true", help="Search mods")
	group.add_argument("--cc", nargs='?', const=True, metavar="SUBOPERATION", help="Clear cache")
	group.add_argument("--instance", nargs="+", metavar=("SUBOPERATION", "NAME", "PATH"), help="Instance operations")
	group.add_argument("--version", action="store_true")

	parser.add_argument("-a", "--all", action="store_true", help="Apply to all")
	parser.add_argument("-e", "--explicit", action="store_true", help="Explicit")
	parser.add_argument("-d", "--dependency", action="store_true", help="Dependency")
	parser.add_argument("-p", "--optional", action="store_true", help="Optional")
	parser.add_argument("-y", "--noconfirm", action="store_true", help="Skip the confirmation dialogue, does not skip the ignore question in downgrade")
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
	result["lock"] = result.get("operation") in ["sync", "update", "remove", "toggle", "downgrade"]
	return result

class InvalidOption(Exception):
	"error: invalid option"

config_dir = appdirs.user_config_dir("ekno/mcmodman")

exe_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)) 

if not os.path.exists(config_dir):
	os.makedirs(config_dir)

if not os.path.exists(os.path.expanduser(os.path.join(config_dir, "config.toml"))):
	if not os.path.exists(os.path.join(exe_path, "config-template.toml")):
		raise FileNotFoundError
	with open(os.path.expanduser(os.path.join(config_dir, "config.toml")), "w", encoding="utf-8") as f:
		config = toml.load(os.path.join(exe_path, "config-template.toml"))
		config["cache-dir"] = appdirs.user_cache_dir("ekno/mcmodman")
		config["log-file"] = os.path.join(config_dir, "mcmodman.log")
		toml.dump(config, f)
else:
	config = toml.load(os.path.join(config_dir, "config.toml"))

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

if not os.path.exists(os.path.join(config_dir, "instances.toml")):
	with open(os.path.join(config_dir, "instances.toml"), 'w',  encoding='utf-8') as f:
		instances = {"dotminecraft": {"name": ".minecraft", "path": "~/.minecraft"}}
		toml.dump(instances, f)
else:
	instances = toml.load(os.path.join(config_dir, "instances.toml"))
logger.info("instances %s", instances)

cacheDir = config["cache-dir"]
logger.info("Cache directory: %s", cacheDir)
if not os.path.exists(cacheDir):
	os.makedirs(cacheDir)
	os.makedirs(os.path.join(cacheDir, "mods"))

if args["operation"] != "instance":
	selected_instance = config["selected-instance"]
	if selected_instance in instances.keys():
		instance_dir = os.path.expanduser(instances[selected_instance]["path"])
	else:
		print("selected instance not found")
		raise SystemExit

	if not os.path.exists(os.path.join(instance_dir, "mcmodman_managed.toml")):
		instanceFirstrun(instance_dir)

	instancecfg = toml.load(os.path.join(instance_dir, "mcmodman_managed.toml"))
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]

	logger.info("instance %s", instancecfg)

	loaderUpstreams = {"quilt": ["fabric"], "neoforge": ["forge"], "folia": ["paper","spigot","bukkit"], "purpur": ["paper","spigot","bukkit"], "paper": ["spigot","bukkit"], "spigot": ["bukkit"]}
