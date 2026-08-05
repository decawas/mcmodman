"""
defines common variables, and meta-instance functions
"""
import logger as logging
import os, sys, appdirs, sqlite3
from configobj import ConfigObj

__version__ = "v26.26"
logger = logging.getLogger()
logger.info("Starting mcmodman version %s", __version__)

class InvalidOption(Exception):
	"error: invalid option"

class Context():
	args: dict
	config: ConfigObj
	instance: dict
	instanceDir: str
	instanceDB: sqlite3.Connection
	loaderUpstreams: dict
	color: str

ctx = Context()

config_dir = os.path.join(appdirs.user_config_dir(), "ekno", "mcmodman")
exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

if not os.path.exists(config_dir):
	os.makedirs(config_dir)

config_file = os.getenv("MCMMCONFIG", os.path.expanduser(os.path.join(appdirs.user_config_dir(), "ekno", "mcmodman", "mcmodman.conf")))
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
	ctx.config["cache-dir"] = os.path.join(appdirs.user_cache_dir(), "ekno", "mcmodman")
	ctx.config["log-file"] = os.path.join(config_dir, "mcmodman.log")
	ctx.config["instances"] = {}
	ctx.config["instances"]["dotminecraft"] = {"name": ".minecraft", "path": os.path.expanduser("%AppData%\\roaming\\.minecraft" if "win" in sys.platform else "~/Library/Application Support/minecraft" if "darwin" in sys.platform else "~/.minecraft")}
	ctx.config.filename = config_file
	ctx.config.write()
else:
	ctx.config = ConfigObj(config_file, unrepr=True)

if os.path.exists(ctx.config["log-file"]) and os.path.getsize(ctx.config["log-file"]) > 4194304:
	os.remove(ctx.config["log-file"])
logger.basicConfig(filename=ctx.config["log-file"], level=logging.NOTSET)

logger.debug("Config directory: %s", config_dir)
logger.debug(ctx.config)

if "instances" not in ctx.config:
	ctx.config["instances"]  = {}
	ctx.instanceDir = ctx.config.get("instances-file", os.path.join(config_dir, "instances.ini"))
	if not any([os.path.exists(ctx.instanceDir), os.path.exists(os.path.join(config_dir, "instances.toml"))]):
		ctx.config["instances"]["dotminecraft"] = {"name": ".minecraft", "path": os.path.expanduser("%AppData%\\roaming\\.minecraft" if "win" in sys.platform else "~/Library/Application Support/minecraft" if "darwin" in sys.platform else "~/.minecraft")}
	elif os.path.exists(ctx.instanceDir):
		instance = ConfigObj(unrepr=True, encoding='utf-8')
		ctx.config["instances"] = dict(instance)
		os.remove(ctx.instanceDir)
	elif os.path.exists(os.path.join(config_dir, "instances.toml")):
		import tomlkit
		with open(os.path.join(config_dir, "instances.toml"), "r") as f:
			instance = tomlkit.load(f)
		ctx.config["instances"] = instance
		os.remove(os.path.join(config_dir, "instances.toml"))
	ctx.config.write()

logger.info("Cache directory: %s", ctx.config["cache-dir"])
if not os.path.exists(ctx.config["cache-dir"]):
	os.makedirs(ctx.config["cache-dir"])
	os.makedirs(os.path.join(ctx.config["cache-dir"], "mods"))

for arg in sys.argv:
	if "mcmodman" in arg:
		ctx.args = sys.argv[sys.argv.index(arg) + 1:]
		break

shortflags = "".join([arg.replace("-", "") for arg in ctx.args if arg.startswith("-") and not arg.startswith("--")])
longflags = [arg.replace("--", "") for arg in ctx.args if arg.startswith("--")]
slugs = [arg for arg  in ctx.args if not arg.startswith("-")]

ops = [flag for flag in longflags if flag in ["sync", "upgrade", "downgrade", "remove", "toggle", "query", "search", "cc", "instance", "version"]]
ops.extend([flag for flag in shortflags if flag in ["S", "U", "D", "R", "T", "Q", "F"]])
if len(ops) > 1:
	print("error: only use one operation at a time")
	logger.error("user used multiple operations: %s", ops)
	raise SystemExit
if not ops:
	print("error: no operation specified")
	logger.error("user did not specify an operation")
	raise SystemExit

if "asdeps" in longflags and "asexplicit" in longflags: raise SystemExit

if ops[0] in ["instance", "version"] and slugs:
	print(f"error: this operation takes 0 arguments, {len(slugs)} given")
	logger.error("user gave too many arguments")
	raise SystemExit

ctx.args = {}
if ops[0] in ["S", "sync"]: ctx.args["operation"] = "sync"
elif ops[0] in ["U", "upgrade"]: ctx.args["operation"] = "upgrade"
elif ops[0] in ["D", "downgrade"]: ctx.args["operation"] = "downgrade"
elif ops[0] in ["R", "remove"]: ctx.args["operation"] = "remove"
elif ops[0] in ["F", "search"]: ctx.args["operation"] = "search"
elif ops[0] in ["Q", "query"]: ctx.args["operation"] = "query"
elif ops[0] in ["T", "toggle"]: ctx.args["operation"] = "toggle"
elif ops[0] in ["instance", "version"]: ctx.args["operation"] = ops[0]
elif ops[0] in ["cc"]: ctx.args["operation"] = "clear-cache"

ctx.args["asexplicit"] = "asexplicit" in longflags
ctx.args["asdeps"] = "asdeps" in longflags

if ctx.args["operation"] == "search":
	ctx.args["query"] = " ".join(slugs)
elif ctx.args["operation"] == "clear-cache":
	ctx.args["suboperation"] = "" if not slugs else slugs[0]
elif ctx.args["operation"] == "instance":
	ctx.args["suboperation"] = slugs[0]
	ctx.args["name"] = slugs[1] if len(slugs) > 1 else None
	ctx.args["path"] = slugs[2] if len(slugs) > 2 else None
else:
	ctx.args["slugs"] = slugs

ctx.args["all"] = "a" in shortflags or "all" in longflags
ctx.args["explicit"] = "e" in shortflags or "explicit" in longflags
ctx.args["dependency"] = "d" in shortflags or "dependency" in longflags
ctx.args["optional"] = "p" in shortflags or "optional" in longflags
ctx.args["noconfirm"] = "noconfirm" in longflags
ctx.args["color"] = "c" in shortflags or "color" in longflags
ctx.args["info"] = "i" in shortflags or "info" in longflags
ctx.args["ignore"] = "ignore" in longflags
ctx.args["dbonly"] = "dbonly" in longflags
ctx.lockneeded = ctx.args["operation"] in ["sync", "upgrade", "remove", "toggle", "downgrade"]
logger.debug("Arguments: %s", ctx.args)

class color():
	NORMAL = "\033[0m"
	INPUT = "\033[94m" if ctx.args["color"] or ctx.config.get("Color", False) or ctx.config.get("color", False) else "\033[0m"
	ERROR = "\033[91m" if ctx.args["color"] or ctx.config.get("Color", False) or ctx.config.get("color", False) else "\033[0m"
ctx.color = color()

if ctx.args["operation"] != "instance" or (ctx.args["operation"] == "instance" and ctx.args["suboperation"] == "export"):
	if ctx.config["selected-instance"] in ctx.config["instances"]:
		ctx.instanceDir = os.path.expanduser(ctx.config["instances"][ctx.config["selected-instance"]]["path"])
	else:
		print("selected instance not found")
		raise SystemExit
	logger.info("selected instance: %s", ctx.config["selected-instance"])

	ctx.loaderUpstreams = {"quilt": ["fabric"], "neoforge": ["forge"], "folia": ["paper"], "purpur": ["paper","spigot","bukkit"], "paper": ["spigot","bukkit"], "spigot": ["bukkit"]}
