# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606
import argparse, hashlib, os, toml, time, instance

__version__ = "24.309rv1" # 24,11,05

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
	os.system(f"cp {filename} {instance.instance_dir}/{instance.instancecfg["modfolder"]}/{filename}") # TODO: change a to cross platform call
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
	with open(f"{instance.instance_dir}/.content/{filename}.mm.toml", "w", encoding="utf-8") as f:
		toml.dump(index, f)
	print(f"Mod '{filename}' successfully added")
	return "Added"

def add_mod(slugs):
	indexes = []
	for slug in slugs:
		if os.path.exists(f"{instance.instance_dir}/.content/{slug}.mm.toml"):
			indexes.append(toml.load(f"{instance.instance_dir}/.content/{slug}.mm.toml"))
		elif not args.U:
			indexes.append({"slug": f"{slug}","filename": "-", "version": "None", "version-id": "None"})

	if not indexes:
		print("all mods updated or not found")
		return "No mod"

	api_data, parsed, parsed2, slugs2, indexes2 = [], [], [], [], []
	for slug in slugs:
		api_data.append(modrinth.get_api(slug))
	i, j = 0, len(slugs)
	while i < j:
		parsed.append(modrinth.parse_api(api_data[i])[0])
		if isinstance(parsed[-1], str):
			pass
		elif not parsed[-1]["id"] == indexes[i]["version-id"]:
			parsed2.append(parsed[i])
			slugs2.append(slugs[i])
			indexes2.append(indexes[i])
		i += 1

	confirm(slugs2, parsed2, indexes2)
	for i, slug in enumerate(slugs2):
		modrinth.get_mod(slug, parsed2[i], indexes2[i])
		indexing.mcmm(slug, parsed[i])
		if not os.path.exists(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{parsed[i]['files'][0]['filename']}.mm.toml"):
			print(f"Caching mod '{slug}'")
			os.system(f"cp {instance.instance_dir}/{instance.instancecfg["modfolder"]}/{parsed[i]['files'][0]['filename']} {instance.cachedir}/mods/{parsed[i]['files'][0]['filename']}")
			os.system(f"cp {instance.instance_dir}/.content/{slug}.mm.toml {instance.cachedir}/mods/{parsed[i]['files'][0]['filename']}.mm.toml")
		print(f"Mod '{slug}' successfully updated")

def remove_mod(slugs):
	for slug in slugs:
		if os.path.exists(f"{instance.instance_dir}/.content/{slug}.mm.toml"):
			index = toml.load(f"{instance.instance_dir}/.content/{slug}.mm.toml")
			os.remove(f"{instance.instance_dir}/.content/{slug}.mm.toml")
			os.remove(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}")
			if "index-compatibility" in instance.instancecfg:
				os.remove(f"{instance.instance_dir}/.content/{slug}.pw.toml")
			print(f"Removed mod '{slug}'")
		else:
			print(f"Mod '{slug}' is not installed")

def confirm(slugs, mod_data, indexes):
	print("")
	totaloldsize = 0
	totalnewsize = 0
	for i, data in enumerate(mod_data):
		totalnewsize += data['files'][0]['size']
	for index in indexes:
		if os.path.exists(f'{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index["filename"]}'):
			totaloldsize += os.path.getsize(f'{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index["filename"]}')
		else:
			pass

	for i, slug in enumerate(slugs):
		print(f"Mod {slug} {indexes[i]["version"]} --> {mod_data[i]["version_number"]}")
	print(f"\nTotal download size: {convert_bytes(totalnewsize)}")
	print(f"Net upgrade Size: {convert_bytes(totalnewsize - totaloldsize)}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		raise SystemExit
	else:
		return "Yes"

def query_mod(slugs):
	for slug in slugs:
		if isinstance(slug, bool):
			for file in os.listdir(f"{instance.instance_dir}/.content"):
				if ".mm.toml" in file:
					index = toml.load(f"{instance.instance_dir}/.content/{file}")
					print(f"{file[:-8]} {index["version"]}")
		elif isinstance(slug, str):
			if os.path.exists(f"{instance.instance_dir}/.content/{slug}.mm.toml"):
				index = toml.load(f"{instance.instance_dir}/.content/{slug}.mm.toml")
				print(f"{slug} {index['version']}")
			else:
				print(f"Mod '{slug}' was not found")

def toggle_mod(slugs):
	for slug in slugs:
		index = toml.load(f"{instance.instance_dir}/.content/{slug}.mm.toml")
		if os.path.exists(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index["filename"]}"):
			os.rename(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']} {instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}.disabled")
			print(f"Mod '{slug}' has been disabled")
		elif os.path.exists(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index["filename"]}.disabled"):
			os.rename(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}.disabled {instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}")
			print(f"Mod '{slug}' has been enabled")

def clear_cache():
	if args.Rc and len(os.listdir(f'{instance.cachedir}/modrinth-api')) != 0:
		for file in os.listdir(f"{instance.cachedir}/modrinth-api"):
			cache_data = toml.load(f"{instance.cachedir}/modrinth-api/{file}")
			if time.time() - cache_data["time"] > instance.config["api-expire"] and cache_data["api-cache-version"] == 1:
				os.remove(f"{instance.cachedir}/modrinth-api/{file}")
				print(f"Deleted cache for {file[:-8]}")
			else:
				pass
	if args.Rcc or args.Rccc and len(os.listdir(f'{instance.cachedir}/modrinth-api')) != 0:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return "No clear"
		else:
			for file in os.listdir(f"{instance.cachedir}/modrinth-api"):
				os.remove(f"{instance.cachedir}/modrinth-api/{file}")
				print(f"Deleted api cache for {file[:-8]}")
	if args.Rccc and len(os.listdir(f'{instance.cachedir}/mods')) != 0:
		print("Are you sure you want to clear mod cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing mod cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return "No clear"
		else:
			for file in os.listdir(f"{instance.cachedir}/mods"):
				if file.endswith(".jar"):
					os.remove(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{file}")
					print(f"Deleted mod cache for {file}")
				elif file.endswith(".mm.toml"):
					os.remove(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{file}")
					print(f"Deleted index cache for {file[:-8]}")
	print("Finished clearing cache")

def convert_bytes(size):
	for unit in ['B', 'KB', 'MB']:
		if size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}"

def main():
	if os.path.exists(f"{instance.instance_dir}/mcmodman.lock"):
		print("mcmodman is already running for this instance")
		raise SystemExit
	else:
		os.system(f"touch {instance.instance_dir}/mcmodman.lock")

	if args.S:
		add_mod(args.S)
	elif args.Sf:
		add_file(args.S)
	elif args.U and isinstance(args.U, str):
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
	elif args.version:
		print(__version__)
	elif os.path.exists(os.path.expanduser(f"{instance.instance_dir}/mcmodman_managed.toml")):
		print("No operation specified")
		parser.print_help()
		raise SystemExit

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='mcmodman')
	parser.add_argument('-S', nargs='+', type=str, help='-S [mod_slug]')
	parser.add_argument('-Sf', nargs='?', type=str, help='-S [mod_slug]')
	parser.add_argument('-U', nargs='+', type=str, help='-U [mod_slug]')
	parser.add_argument('-R', nargs='+', type=str, help='-R [mod_slug]')
	parser.add_argument('-Rc', action="store_true", help='-Rc')
	parser.add_argument('-Rcc', action="store_true", help='-Rcc')
	parser.add_argument('-Rccc', action="store_true", help='-Rccc')
	parser.add_argument('-Q', nargs='?', const=True, type=str, help='-Q [mod_slug]')
	parser.add_argument('-T', nargs='?', const=True, type=str, help='-T [mod_slug]')
	parser.add_argument('--version', action="store_true", help='-T [mod_slug]')
	args=parser.parse_args()

	import modrinth, indexing

	try:
		main()
	except KeyboardInterrupt:
		print("Interrupt signal received")
	except Exception as e:
		print("An unexpected error occured")
		raise
	finally:
		os.remove(os.path.expanduser(f"{instance.instance_dir}/mcmodman.lock"))
