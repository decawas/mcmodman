# pylint: disable=E0601 disable=C0114 disable=C0115 disable=C0116 disable=C0411 disable=C0103 disable=W0707 disable=C0410 disable=C0321
import argparse, hashlib, os, toml, time, indexing, modrinth

def instance_firstrun():
	global mod_loader, minecraft_version
	import re
	managefile = "# this instance is managed by mcmodman\n# please do not change any files that might break mcmodman"
	loaders = []

	log = open(f"{instance_dir}/logs/latest.log", "r", encoding="utf-8").read()

	if os.path.exists(f"{instance_dir}/.fabric"):
		loaders.append("fabric")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
	if os.path.exists(f"{instance_dir}/config/quilt-loader.txt"):
		loaders.append("quilt")
		match = re.search(r'Minecraft (\d+(?:\.\d+)*) with', log)
	if os.path.exists(f"{instance_dir}/config/neoforge-client.toml"):
		loaders.append("neoforge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
	if os.path.exists(f"{instance_dir}/config/forge-client.toml"):
		loaders.append("forge")
		match = re.search(r'--version, (\d+(?:\.\d+)*),', log)
	if os.path.exists(f"{instance_dir}/config/liteconfig"):
		loaders.append("liteloader")
		match = re.search(r'LiteLoader (\d+(?:\.\d+)*)\n', log)

	if len(loaders) > 1:
		print("mcmodman does not support instances with multiple loaders")
		return "Multiple Loader"
	elif len(loaders) < 1:
		print("Could not find any mod loaders for this instance\nif you are using Rift or RML you will have to manually set that")
		return "No Loader"
	managefile += f"\nloader = \"{loaders[0]}\""
	mod_loader = loaders[0]
	print(mod_loader)

	if match:
		minecraft_version = str(match.group(1))
		managefile += f"\nversion = \"{match.group(1)}\""
		print(minecraft_version)
	else:
		return "No version"

	if os.path.exists(f"{instance_dir}/crafty_managed.txt"):
		print("WARNING: THIS INSTANCE IS MANAGED BY CRAFTY CONTROLLER\nUSING mcmodman ON THIS INSTANCE MAY BREAK CERTAIN FEATURES OF CRAFTY CONTROLLER")
		yn = input("If you wish to continue, type \"I understand, Break Crafty Controller management!\": ")
		if yn != 'I understand, Break Crafty Controller management!':
			print("Exiting")
			raise SystemExit
		print()
	if os.path.exists(f"{instance_dir}/../instance.cfg"):
		print("mcmodman has detected that this instance is managed by prism launcher\nwould you like to enable dual indexing for prism launcher compatibility?")
		prismcomp = input(":: Enable dual indexing? [Y/n]: ")
		if prismcomp.lower() == "y" or prismcomp == "":
			managefile += "\nindex-compatibility = \"prism\""
	if os.path.exists(f"{instance_dir}/../../profiles"):
		print("mcmodman has detected that this instance is managed by modrinth\n")

	with open(f"{instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
		f.write(managefile)
	if not os.path.exists(f"{instance_dir}/mods/.index"):
		os.makedirs(f"{instance_dir}/mods/.index")

def add_file(filename):
	if not os.path.exists(filename):
		print("The specified file does not exist")
		return "No file"
	if not filename.endswith(".jar"):
		print(f"file '{filename}' is not a jar file")
		return "No jar"
	print(f"\nMod '{filename}' Unknown version\n" )
	yn = input("Proceed with addition? [Y/n]: ")
	if yn.lower() != 'y' and yn.lower() != '':
		return "No add"
	print("Moving file")
	os.system(f"cp {filename} {instance_dir}/mods/{filename}")
	print("Indexing mod")
	index = {}
	index['index-version'] = 1
	index['filename'] = filename
	index['slug'] = filename
	index['mod-id'] = filename
	index['version'] = "Unknown"
	index['version-id'] = "XXXX"
	index['hash'] = hashlib.sha512(open(filename, 'rb').read())
	index['hash-format'] ='sha512'
	index['mode'] = 'file'
	index['source'] = 'local'
	with open(f"{instance_dir}/mods/.index/{filename}.mm.toml", "w", encoding="utf-8") as f:
		toml.dump(index, f)
	print(f"Mod '{filename}' successfully added")
	return "Added"

def add_mod(slug):
	if os.path.exists(f"{instance_dir}/mods/.index/{slug}.mm.toml"):
		index = toml.load(f"{instance_dir}/mods/.index/{slug}.mm.toml")
	elif not args.U:
		index = {"filename": "-", "version": "None", "version-id": "None"}
	else:
		print(f"Mod '{slug}' not installed")
		return "No mod"

	api_data = modrinth.get_api(slug)[1]
	parsed = modrinth.parse_api(api_data)[0]
	if isinstance(parsed, str):
		return parsed
	elif parsed["id"] == index["version-id"]:
		print(f"Mod '{slug}' is already up to date")
		return "up to date"
	confirm(slug, parsed, index)
	modrinth.get_mod(slug, parsed, index)
	indexing.mcmm(slug, parsed)
	if not os.path.exists(f"{cachedir}/mods/{parsed['files'][0]['filename']}.mm.toml"):
		print(f"Caching mod '{slug}'")
		os.system(f"cp {instance_dir}/mods/{parsed['files'][0]['filename']} {cachedir}/mods/{parsed['files'][0]['filename']}")
		os.system(f"cp {instance_dir}/mods/.index/{slug}.mm.toml {cachedir}/mods/{parsed['files'][0]['filename']}.mm.toml")
	print(f"Mod '{slug}' successfully updated")

def remove_mod(slug):
	if os.path.exists(f"{instance_dir}/mods/.index/{slug}.mm.toml"):
		index = toml.load(f"{instance_dir}/mods/.index/{slug}.mm.toml")
		os.system(f"rm -f {instance_dir}/mods/{index['filename']}")
		os.system(f"rm -f {instance_dir}/mods/.index/{slug}.mm.toml")
		os.system(f"rm -f {instance_dir}/mods/.index/{slug}.pw.toml")
		print(f"Removed mod '{slug}'")
	else:
		print(f"Mod '{slug}' is not installed")
		return "No mod"

def confirm(slug, mod_data, index):
	print(f"\nMod {slug} {index["version"]} --> {mod_data["version_number"]}\n")
	print(f"Total download size: {convert_bytes(mod_data['files'][0]['size'])}")
	if os.path.exists(f'{instance_dir}/mods/{index["filename"]}'):
		print(f"Net upgrade Size: {convert_bytes(mod_data['files'][0]['size'] - os.path.getsize(f'{instance_dir}/mods/{index["filename"]}'))}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		raise SystemExit
	else:
		return "Yes"

def query_mod(slug):
	if isinstance(slug, bool):
		for file in os.listdir(f"{instance_dir}/mods/.index"):
			if ".mm.toml" in file:
				index = toml.load(f"{instance_dir}/mods/.index/{file}")
				print(f"{file[:-8]} {index["version"]}")
	elif isinstance(slug, str):
		if os.path.exists(f"{instance_dir}/mods/.index/{slug}.mm.toml"):
			index = toml.load(f"{instance_dir}/mods/.index/{slug}.mm.toml")
			print(f"{slug} {index['version']}")
		else:
			print(f"Mod '{slug}' was not found")

def toggle_mod(slug):
	index = toml.load(f"{instance_dir}/mods/.index/{slug}.mm.toml")
	if os.path.exists(f"{instance_dir}/mods/{index["filename"]}"):
		os.system(f"mv {instance_dir}/mods/{index['filename']} {instance_dir}/mods/{index['filename']}.disabled")
		print(f"Mod '{slug}' has been disabled")
	elif os.path.exists(f"{instance_dir}/mods/{index["filename"]}.disabled"):
		os.system(f"mv {instance_dir}/mods/{index['filename']}.disabled {instance_dir}/mods/{index['filename']}")
		print(f"Mod '{slug}' has been enabled")

def clear_cache():
	if args.Rc and len(os.listdir(f'{cachedir}/modrinth-api')) != 0:
		for file in os.listdir(f"{cachedir}/modrinth-api"):
			cache_data = toml.load(f"{cachedir}/modrinth-api/{file}")
			if time.time() - cache_data["time"] > config["api-expire"] and cache_data["api-cache-version"] == 1:
				os.system(f"rm {cachedir}/modrinth-api/{file}")
				print(f"Deleted cache for {file[:-8]}")
			else:
				pass
	if args.Rcc or args.Rccc and len(os.listdir(f'{cachedir}/modrinth-api')) != 0:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return "No clear"
		else:
			for file in os.listdir(f"{cachedir}/modrinth-api"):
				os.system(f"rm {cachedir}/modrinth-api/{file}")
				print(f"Deleted api cache for {file[:-8]}")
	if args.Rccc and len(os.listdir(f'{cachedir}/mods')) != 0:
		print("Are you sure you want to clear mod cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing mod cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return "No clear"
		else:
			for file in os.listdir(f"{cachedir}/mods"):
				if file.endswith(".jar"):
					os.system(f"rm {cachedir}/mods/{file}")
					print(f"Deleted mod cache for {file}")
				elif file.endswith(".mm.toml"):
					os.system(f"rm {cachedir}/mods/{file}")
					print(f"Deleted index cache for {file[:-8]}")
	print("Finished clearing cache")

def convert_bytes(size):
	for unit in ['B', 'KB', 'MB']:
		if size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}"

def main():
	if os.path.exists(f"{instance_dir}/mcmodman.lock"):
		print("mcmodman is already running for this instance")
		exit(1)
	else:
		os.system(f"touch {instance_dir}/mcmodman.lock")

	if not os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
		instance_firstrun()
	if args.S:
		add_mod(args.S)
	elif args.Sf:
		add_file(args.Sf)
	elif args.U:
		add_mod(args.U)
	elif args.R:
		remove_mod(args.R)
	elif args.Rc or args.Rcc or args.Rccc:
		clear_cache()
	elif args.Q:
		try:
			query_mod(args.Q)
		except FileNotFoundError:
			print("No mods installed")
	elif args.T:
		toggle_mod(args.T)
	else:
		print("No operation specified")
		parser.print_help()
		exit(1)

	os.system(f"rm {instance_dir}/mcmodman.lock")

if __name__ == "__main__":
	if os.path.exists(os.path.expanduser("~/.config/ekno/mcmodman/config.toml")):
		config = toml.load(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"))
	else:
		config = {"instances": [{"name": ".minecraft", "path": "~/.minecraft", "id": "0"}], "cache-dir": "autodetect", "include-beta": False, "api-expire": 3600, "checksum": "Always"}
		os.makedirs(os.path.expanduser("~/.config/ekno/mcmodman"))
		toml.dump(config, open(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"), 'w',  encoding='utf-8'))

	if config['cache-dir'] == "autodetect":
		cachedir = os.path.expanduser("~/.cache/ekno/mcmodman")
	elif config['cache-dir'] != "autodetect":
		cachedir = os.path.expanduser(config['cache-dir'])
	if not os.path.exists(cachedir):
		os.makedirs(cachedir)
		os.makedirs(f"{cachedir}/mods")
		os.makedirs(f"{cachedir}/modrinth-api")

	instance_dir = config['instances'][0]["path"]
	print(instance_dir)

	if os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
		instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
		mod_loader = instancecfg["loader"]
		minecraft_version = instancecfg["version"]
	else:
		mod_loader = ""
		minecraft_version = ""

	parser = argparse.ArgumentParser(description='mcmodman')
	parser.add_argument('-S', nargs='?', const=True, type=str, help='-S [mod_slug]')
	parser.add_argument('-Sf', nargs='?', const=True, type=str, help='-Sf [mod_slug]')
	parser.add_argument('-U', nargs='?', const=True, type=str, help='-U [mod_slug]')
	parser.add_argument('-R', nargs='?', const=True, type=str, help='-R [mod_slug]')
	parser.add_argument('-Rc', action="store_true", help='-Rc')
	parser.add_argument('-Rcc', action="store_true", help='-Rcc')
	parser.add_argument('-Rccc', action="store_true", help='-Rccc')
	parser.add_argument('-Q', nargs='?', const=True, type=str, help='-Q [mod_slug]')
	parser.add_argument('-T', nargs='?', const=True, type=str, help='-T [mod_slug]')
	args=parser.parse_args()

	try:
		main()
	except KeyboardInterrupt:
		print("Interrupt signal received")
