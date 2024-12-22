# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606 W1203 I1101
# pylint: disable=W0718
import os, toml
import logging
from shutil import copyfile
from time import time

__version__ = "sparrow-1f49d1c28e9+1"

def add_mod(slugs):
	indexes = []
	for slug in slugs:
		if os.path.exists(f"{commons.instance_dir}/.content/{slug}.mm.toml"):
			indexes.append(toml.load(f"{commons.instance_dir}/.content/{slug}.mm.toml"))
			logger.info(f"Loaded index for mod '{slug}'")
		elif not commons.args.update:
			indexes.append({"slug": f"{slug}","filename": "-", "version": "None", "version-id": "None"})
			logger.info(f"Created dummy index for mod new '{slug}'")

	if not indexes:
		print("all mods updated or not found")
		return "No mod"

	api_data, parsed, parsed2, slugs2, indexes2 = [], [], [], [], []
	for slug in slugs:
		api_data.append(modrinth.get_api(slug))
		if isinstance(api_data, dict):
			logger.info(f"Successfully got api_data for mod '{slug}'")
	i, j = 0, len(slugs)
	while i < j:
		parsed.append(modrinth.parse_api(api_data[i])[0])
		if isinstance(parsed[-1], str):
			pass
		elif parsed[-1]["id"] != indexes[i]["version-id"]:
			parsed2.append(parsed[i])
			slugs2.append(slugs[i])
			indexes2.append(indexes[i])
		i += 1

	if not parsed2:
		print("all mods up to date")
		return "No mod"

	confirm(slugs2, parsed2, indexes2)
	for i, slug in enumerate(slugs2):
		modrinth.get_mod(slug, parsed2[i], indexes2[i])
		logger.info(f"Sucessfully downloaded content '{slug}' ({parsed2[i]['files'][0]['size']} B)")
		indexing.mcmm(slug, parsed[i])
		if not os.path.exists(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{parsed[i]['files'][0]['filename']}.mm.toml"):
			print(f"Caching mod '{slug}'")
			copyfile(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{parsed[i]['files'][0]['filename']}", f"{commons.cache_dir}/mods/{parsed[i]['files'][0]['filename']}")
			copyfile(f"{commons.instance_dir}/.content/{slug}.mm.toml", f"{commons.cache_dir}/mods/{parsed[i]['files'][0]['filename']}.mm.toml")
			logger.info(f"Copied content '{slug}' to cache")
		print(f"Mod '{slug}' successfully updated")

def remove_mod(slugs):
	for slug in slugs:
		if os.path.exists(f"{commons.instance_dir}/.content/{slug}.mm.toml"):
			# TODO: add confirmation dialogue here
			index = toml.load(f"{commons.instance_dir}/.content/{slug}.mm.toml")
			os.remove(f"{commons.instance_dir}/.content/{slug}.mm.toml")
			os.remove(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}")
			logger.info(f"Removed content '{slug}'")
			if "index-compatibility" in commons.instancecfg:
				os.remove(f"{commons.instance_dir}/.content/{slug}.pw.toml")
			print(f"Removed mod '{slug}'")
		else:
			print(f"Mod '{slug}' is not installed")
			logger.error(f"Could not remove content '{slug}' because it is not installed")

def confirm(slugs, mod_data, indexes):
	print("")
	totaloldsize = sum(os.path.getsize(f'{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index["filename"]}') for index in indexes if os.path.exists(f'{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index["filename"]}'))
	totalnewsize = sum(data['files'][0]['size'] for data in mod_data)

	for i, slug in enumerate(slugs):
		print(f"Mod {slug} {indexes[i]["version"]} --> {mod_data[i]["version_number"]}")
	print(f"\nTotal download size: {convert_bytes(totalnewsize)}")
	print(f"Net upgrade Size: {convert_bytes(totalnewsize - totaloldsize)}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		raise RuntimeError("User declined download")
	return "Yes"

def query_mod(slugs):
	if not slugs:
		for file in os.listdir(f"{commons.instance_dir}/.content"):
			if ".mm.toml" in file:
				index = toml.load(f"{commons.instance_dir}/.content/{file}")
				print(f"{file[:-8]} {index["version"]}")
				logger.info(f"Found mod {file}")
	else:
		for slug in slugs:
			if os.path.exists(f"{commons.instance_dir}/.content/{slug}.mm.toml"):
				index = toml.load(f"{commons.instance_dir}/.content/{slug}.mm.toml")
				print(f"{slug} {index['version']}")
				logger.info(f"Found mod {slug} ({index["mod-id"]}) version {index["version"]} ({index["version-id"]})")
			else:
				print(f"Mod '{slug}' was not found")
				logger.info(f"Couldnt find index for mod {slug}")

def toggle_mod(slugs):
	for slug in slugs:
		index = toml.load(f"{commons.instance_dir}/.content/{slug}.mm.toml")
		if os.path.exists(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index["filename"]}"):
			os.rename(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']} {commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}.disabled")
			index['filename'] = f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}.disabled"
			print(f"Mod '{slug}' has been disabled")
			logger.info(f"Moved content '{slug}' from {index['filename']} to {index['filename']}.disabled")
		elif os.path.exists(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index["filename"]}.disabled"):
			os.rename(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}.disabled {commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}")
			index['filename'] = f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}"
			print(f"Mod '{slug}' has been enabled")
			logger.info(f"Moved content '{slug}' from {index['filename']}.disabled to {index['filename']}")

def clear_cache():
	if commons.args.cc and len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			cache_data = toml.load(f"{commons.cache_dir}/modrinth-api/{file}")
			if time() - cache_data["time"] > commons.config["api-expire"] and cache_data["api-cache-version"] != 2:
				os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
				print(f"Deleted api cache for {file[:-8]} (expired)")
				logger.info(f"Deleted cache for {file[:-8]}")
	if commons.args.cc == any(["api", "content"]) and len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return "No clear"
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
			print(f"Deleted api cache for {file[:-8]}")
			logger.info(f"Deleted api cache for {file[:-8]} (clear all)")
	if commons.args.cc == "content" and len(os.listdir(f'{commons.cache_dir}/mods')) != 0:
		print("Are you sure you want to clear content cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing content cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return "No clear"
		for file in os.listdir(f"{commons.cache_dir}/mods"):
			if file.endswith(".jar"):
				os.remove(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{file}")
				print(f"Deleted content cache for {file}")
				logger.info(f"Deleted content cache for {file} (clear content cache)")
			elif file.endswith(".mm.toml"):
				os.remove(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{file}")
				print(f"Deleted index cache for {file[:-8]}")
				logger.info(f"Deleted index cache for {file[:-8]} (clear content cache)")
	print("Finished clearing cache")

def convert_bytes(size):
	for unit in ['B', 'KB', 'MB', 'GB']:
		if size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}"

def main():
	if not commons.args.instance:
		if os.path.exists(f"{commons.instance_dir}/mcmodman.lock"):
			print("mcmodman is already running for this instance")
			logger.info("mcmodman.lock file already exists, exiting")
			return None

		with open(f"{commons.instance_dir}/mcmodman.lock", "w", encoding="utf-8"):
			logger.info("Setting lock")

	if commons.args.addbyslug:
		add_mod(commons.args.addbyslug)
	elif commons.args.update:
		add_mod(commons.args.update)
	elif commons.args.remove:
		remove_mod(commons.args.remove)
	elif commons.args.cc:
		clear_cache()
	elif isinstance(commons.args.query, list):
		query_mod(commons.args.query)
	elif commons.args.toggle:
		toggle_mod(commons.args.toggle)
	elif commons.args.instance:
		if commons.args.instance == "add":
			commons.add_instance()
		if commons.args.instance == "select":
			commons.sel_instance()
		if commons.args.instance == "remove":
			commons.del_instance()
	elif commons.args.version:
		print(__version__)
	else:
		print("No operation specified")
		commons.parser.print_help()
		logger.warning("No operation specified")

if __name__ == "__main__":
	logger = logging.getLogger(__name__)
	logging.basicConfig(filename="testlog.log", level=logging.NOTSET)
	logger.info(f"Starting mcmodman version {__version__}")

	try:
		import commons
		import modrinth, indexing

		main()
	except KeyboardInterrupt:
		print("Interrupt signal received")
		logger.info("Process interrupted by user")
	except RuntimeError as e:
		print("An error occurred while running mcmodman")
		logger.critical(e)
	except Exception as e:
		print("An unexpected error occured")
		logger.critical(e)
	finally:
		if not commons.args.instance and  os.path.exists(os.path.expanduser(f"{commons.instance_dir}")):
			logger.info("Removing lock")
			os.remove(os.path.expanduser(f"{commons.instance_dir}/mcmodman.lock"))
		logger.info("Exiting")
