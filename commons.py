"""
defines common variables, and meta-instance functions
"""
import argparse
import logging, os, sys, appdirs
from typing import Any
from configobj import ConfigObj

__version__ = "25.49rc2"
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
	parser.add_argument("-i", "--info", action="store_true", help="Display information for a given mod")
	parser.add_argument("--ignore", action="store_true", help="Ignore mods")
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
	result["info"] = args.info
	result["ignore"] = args.ignore
	return result

class InvalidOption(Exception):
	"error: invalid option"

class Context():
	args: dict
	config: ConfigObj
	instance: ConfigObj
	instanceDir: str
	lockneeded: bool
	loaderUpstreams: dict
	color: Any

ctx = Context()

config_dir = appdirs.user_config_dir("ekno/mcmodman")
exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

if not os.path.exists(config_dir):
	os.makedirs(config_dir)

config_file = os.getenv("MCMMCONFIG", os.path.expanduser(os.path.join(appdirs.user_config_dir("ekno/mcmodman"), "mcmodman.conf")))
if os.path.exists(os.path.join(config_dir, "config.toml")) and not os.path.exists(config_file):
	import tomlkit
	with open(os.path.join(config_dir, "config.toml"), "r") as f:
		oldconfig = tomlkit.load(f)
	ctx.config = ConfigObj(unrepr=True)
	ctx.config.filename = config_file
	for value in oldconfig:
		ctx.config[value] = oldconfig[value]
	ctx.config.write()
	os.remove(os.path.join(config_dir, "config.toml"))
elif not os.path.exists(config_file):
	if not os.path.exists(os.path.join(exe_dir, "config-template.ini")):
		raise FileNotFoundError
	ctx.config = ConfigObj(os.path.join(exe_dir, "config-template.ini"), unrepr=True)
	ctx.config["cache-dir"] = appdirs.user_cache_dir("ekno/mcmodman")
	ctx.config["log-file"] = os.path.join(config_dir, "mcmodman.log")
	ctx.config.filename = config_file
	ctx.config.write()
else:
	ctx.config = ConfigObj(config_file, unrepr=True)

if os.path.getsize(ctx.config["log-file"]) > 4194304:
	os.remove(ctx.config["log-file"])
logging.basicConfig(filename=ctx.config["log-file"], level=logging.NOTSET)
logger.info("Starting mcmodman version %s", __version__)

logger.info("Config directory: %s", config_dir)
logger.info(ctx.config)

try:
	ctx.args = parse_args()
	ctx.lockneeded = ctx.args["operation"] in ["sync", "upgrade", "remove", "toggle", "downgrade"]
	logger.info("Arguments: %s", ctx.args)
except Exception as e:
	print("error: invalid option")
	logger.critical("invalid option")
	raise

ctx.instanceDir = ctx.config.get("instances-file", os.path.join(config_dir, "instances.ini"))
if os.path.exists(os.path.join(config_dir, "instances.toml")) and not os.path.exists(ctx.instanceDir):
	import tomlkit
	with open(os.path.join(config_dir, "instances.toml"), "r") as f:
		oldinstances = tomlkit.load(f)
	ctx.instance = ConfigObj(unrepr=True, encoding='utf-8')
	ctx.instance.filename = ctx.instanceDir
	for value in oldinstances:
		ctx.instance[value] = oldinstances[value]
	ctx.instance.write()
	os.remove(os.path.join(config_dir, "instances.toml"))
elif not os.path.exists(ctx.instanceDir):
	ctx.instance = ConfigObj(unrepr=True, encoding='utf-8')
	ctx.instance["dotminecraft"] = {"name": ".minecraft", "path": "~/%AppData%/roaming/.minecraft" if "win" in sys.platform else "~/Library/Application Support/minecraft" if "darwin" in sys.platform else "~/.minecraft"}
	ctx.instance.filename = ctx.instanceDir
	ctx.instance.write()
else:
	ctx.instance = ConfigObj(ctx.instanceDir, unrepr=True)

logger.info("instances %s", ctx.instance)

logger.info("Cache directory: %s", ctx.config["cache-dir"])
if not os.path.exists(ctx.config["cache-dir"]):
	os.makedirs(ctx.config["cache-dir"])
	os.makedirs(os.path.join(ctx.config["cache-dir"], "mods"))

class color():
	NORMAL = "\033[0m"
	INPUT = "\033[94m" if ctx.args["color"] or ctx.config.get("Color", False) else "\033[0m"
	ERROR = "\033[91m" if ctx.args["color"] or ctx.config.get("Color", False) else "\033[0m"
ctx.color = color()

if ctx.args["operation"] != "instance":
	if ctx.config["selected-instance"] in ctx.instance:
		ctx.instanceDir = os.path.expanduser(ctx.instance[ctx.config["selected-instance"]]["path"])
	else:
		print("selected instance not found")
		raise SystemExit
	logger.info("selected instance: %s", ctx.config["selected-instance"])

	if os.path.exists(os.path.join(ctx.instanceDir, "mcmodman_managed.ini")):
		ctx.instance = ConfigObj(os.path.join(ctx.instanceDir, "mcmodman_managed.ini"), unrepr=True, encoding='utf-8')
	else:
		from instance import instanceFirstrun
		ctx.instance = instanceFirstrun(ctx)
	logger.info("instance %s", ctx.instance)

	ctx.loaderUpstreams = {"quilt": ["fabric"], "neoforge": ["forge"], "folia": ["paper"], "purpur": ["paper","spigot","bukkit"], "paper": ["spigot","bukkit"], "spigot": ["bukkit"]}
