# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606 W1203 I1101
import os, appdirs, toml, re, logging  # type: ignore
from argparse import ArgumentParser

def instance_firstrun():
	if os.path.exists(os.path.expanduser(f"{instance_dir}/logs/latest.log")):
		with open(os.path.expanduser(f"{instance_dir}/logs/latest.log"), "r", encoding="utf-8") as f:
			log = f.read()
	else:
		print("instance must be run at least once before using mcmodman")
		raise SystemExit

	loaders = []
	if os.path.exists(f"{instance_dir}/config/quilt-loader.txt"): # detect quilt
		loaders.append("quilt")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
		logger.info("found loader 'Quilt'")
	if os.path.exists(f"{instance_dir}/config/neoforge-client.toml") or os.path.exists(f"{instance_dir}/config/neoforge-server.toml"): # detect neoforge
		loaders.append("neoforge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
		logger.info("found loader 'NeoForge'")
	if os.path.exists(f"{instance_dir}/.fabric"): # detect fabric
		loaders.append("fabric")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
		logger.info("found loader 'Fabric'")
	if os.path.exists(f"{instance_dir}/config/forge-client.toml") or os.path.exists(f"{instance_dir}/config/forge-server.toml"): # detect forge
		loaders.append("forge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
		logger.info("found loader 'Forge'")
	if os.path.exists(f"{instance_dir}/config/liteconfig"): # detect liteloader
		loaders.append("liteloader")
		match = re.search(r'LiteLoader (\d+(?:\.\d+)*)\n', log)
		logger.info("found loader 'LiteLoader'")
	if re.search(r'Purpur (\d+(?:\.\d+)*)-', log) is not None: # detect folia
		loaders.append("purpur")
		match = re.search(r'Purpur (\d+(?:\.\d+)*)-', log)
		logger.info("found loader 'Purpur'")
	if re.search(r'Folia version (\d+(?:\.\d+)*)-', log) is not None: # detect folia
		loaders.append("folia")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
		logger.info("found loader 'Folia'")
	if os.path.exists(f"{instance_dir}/config/paper-global.yml") and loaders[0] != any(["folia", "purpur"]): # detect paper
		loaders.append("paper")
		match = re.search(r'Paper (\d+(?:\.\d+)*)-', log)
		logger.info("found loader 'Paper'")
	if os.path.exists(f"{instance_dir}/spigot.yml") and loaders[0] != any(["folia", "purpur", "paper"]): # detect spigot
		loaders.append("spigot")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
		logger.info("found loader 'Spigot'")
	if os.path.exists(f"{instance_dir}/bukkit.yml") and loaders[0] != any(["folia", "purpur", "paper", "spigot"]): # detect bukkit
		loaders.append("bukkit")
		match = re.search(r'server version (\d+(?:\.\d+)*)\n', log)
		logger.info("found loader 'CraftBukkit'")
	if os.path.exists(f"{instance_dir}/config/sponge/sponge.conf"): # detect sponge
		loaders.append("sponge")
		match = re.search(r'spongevanilla-(\d+(?:\.\d+)*)-', log)
		logger.info("found loader 'Sponge'")

	if len(loaders) > 1:
		print("mcmodman does not support instances with multiple loaders")
		raise RuntimeError("mcmodman does not support instances with multiple loaders")
	if not loaders:
		print("Could not find any mod loaders for this instance\nif you are using Rift, RML or have no mod loader you will have to manually set that")
		return "No Loader"
	managefile = {"loader": loaders[0]}

	if re.search(loaders[0], "purpur,folia,paper,spigot,bukkit") is not None:
		managefile["modfolder"] = "plugins"
	if re.search(loaders[0], "quilt,neoforge,sponge,fabric,forge,liteloader") is not None:
		managefile["modfolder"] = "mods"

	if match:
		managefile["version"] = f"{match.group(1)}"
	else:
		return "No version"

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

logger = logging.getLogger(__name__)

parser = ArgumentParser(description='mcmodman')
parser.add_argument('-S', nargs='+', type=str, help='-S [mod_slug]', dest="addbyslug")
parser.add_argument('-U', nargs='+', type=str, help='-U [mod_slug]', dest="update")
parser.add_argument('-R', nargs='+', type=str, help='-R [mod_slug]', dest="remove")
parser.add_argument('-Q', nargs='*', type=str, help='-Q [mod_slug]', dest="query")
parser.add_argument('-T', nargs='+', type=str, help='-T [mod_slug]', dest="toggle")
parser.add_argument('--instance', nargs='?', const=True, type=str, help='instance add|select|remove')
parser.add_argument('-cc', nargs='?', const=True, type=str, help='clear cache, -cc expired|api|all')
parser.add_argument('--version', action="store_true", help='-version')
args=parser.parse_args()

logger.info(f"Arguments: {args}")


config_dir = appdirs.user_config_dir("ekno/mcmodman")
logger.info(f"Config directory: {config_dir}")
if not os.path.exists(config_dir):
	os.makedirs(config_dir)

if os.path.exists(f"{config_dir}/config.toml"):
	config = toml.load(f"{config_dir}/config.toml")
else:
	config = {"include-beta": False, "api-expire": 3600, "checksum": "Always", "selected-instance": "dotminecraft"}
	toml.dump(config, open(f"{config_dir}/config.toml", 'w',  encoding='utf-8'))

if not os.path.exists(f"{config_dir}/instances.toml"):
	instances = {"dotminecraft": {"name": ".minecraft", "path": "~/.minecraft"}}
	toml.dump(instances, open(f"{config_dir}/instances.toml", 'w',  encoding='utf-8'))
else:
	instances = toml.load(f"{config_dir}/instances.toml")
	logger.info(f"instances {instances}")

if not args.instance:
	cache_dir = appdirs.user_cache_dir("ekno/mcmodman")
	logger.info(f"Cache directory: {cache_dir}")
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
		print("suh")

	instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]

	logger.info(f"instance {instancecfg}")
