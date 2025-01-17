# pylint: disable=C0114 C0116 C0410
# pylint: disable=W0718
from shutil import copyfile
from time import time
import logging, os, toml, commons, modrinth, indexing

logger = logging.getLogger(__name__)

def add_mod(slugs):
	mods = [{'slug': slug} for slug in slugs]
	for mod in mods:
		if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml")):
			mod["index"] = toml.load(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml"))
			logger.info("Loaded index for mod '%s'", mod['slug'])
		elif "update" not in commons.args:
			mod["index"] = {"slug": f"{mod['slug']}","filename": "-", "version": "None", "version-id": "None"}
			logger.info("Created dummy index for mod new '%s'", mod['slug'])

	if not any('index' in d for d in mods):
		print("all mods updated or not found")
		return "No mod"

	for mod in reversed(mods):
		mod["api_data"] = modrinth.get_api(mod["slug"])
		if isinstance(mod["api_data"], dict):
			logger.info("Successfully got api_data for mod '%s'", mod['slug'])
			mod["api_data"]["versions"] = modrinth.parse_api(mod["api_data"])
			if isinstance(mod["api_data"], str) or mod["api_data"]["versions"][0]["id"] == mod["index"]["version-id"]:
				mods.remove(mod)

	if not mods:
		print("all mods up to date")
		return "No mod"

	confirm(mods, "download")
	for mod in mods:
		modrinth.get_mod(mod["slug"], mod["api_data"]["versions"][0], mod["index"])
		logger.info("Sucessfully downloaded content '%s' (%s B)", mod['slug'], mod['api_data']['versions'][0]['files'][0]['size'])
		indexing.mcmm(mod['slug'], mod['api_data']['versions'][0])
		if not os.path.exists(os.path.join(commons.cache_dir, commons.instancecfg["modfolder"], f"{mod['api_data']['versions'][0]['files'][0]['filename']}.mm.toml")):
			print(f"Caching mod '{mod['slug']}'")
			copyfile(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod['api_data']['versions'][0]['files'][0]['filename']), os.path.join(commons.cache_dir, "mods", mod['api_data']['versions'][0]['files'][0]['filename']))
			copyfile(f"{commons.instance_dir}/.content/{mod['slug']}.mm.toml", f"{commons.cache_dir}/mods/{mod['api_data']['versions'][0]['files'][0]['filename']}.mm.toml")
			logger.info("Copied content '%s' to cache", {mod['slug']})
		print(f"Mod '{mod['slug']}' successfully updated")

def remove_mod(slugs):
	mods = [{'slug': slug} for slug in slugs]
	for mod in reversed(mods):
		if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml")):
			mod["index"] = (toml.load(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml")))
			logger.info("Loaded index for mod '%s'", {mod['slug']})
		else:
			print(f"Mod '{mod['slug']}' is not installed")
			logger.error("Could not load index '%s' because it is not installed", {mod['slug']})
			mods.remove(mod)

	if not mods:
		print("no mods found")
		return "No mod"

	confirm(mods, "remove")

	for mod in mods:
		os.remove(f"{commons.instance_dir}/.content/{mod['slug']}.mm.toml")
		os.remove(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod['index']['filename']))
		logger.info("Removed content '%s'", {mod['slug']})
		if "index-compatibility" in commons.instancecfg:
			os.remove(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index", f"{mod['slug']}.pw.toml"))
		print(f"Removed mod '{mod['slug']}'")


def confirm(mods, changetype):
	print("")
	totaloldsize = sum(os.path.getsize(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod["index"]["filename"])) for mod in mods if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod["index"]["filename"])))
	totalnewsize = sum(mod["api_data"]["versions"][0]["files"][0]["size"] for mod in mods) if changetype == "download" else 0

	for mod in mods:
		print(f"Mod {mod['slug']} {mod['index']['version']} --> {mod['api_data']['versions'][0]['version_number'] if changetype == 'download' else None}")
	print(f"\nTotal {changetype} size: {convert_bytes(totalnewsize if changetype == 'download' else totaloldsize)}")
	print(f"Net upgrade Size: {convert_bytes(totalnewsize - totaloldsize)}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		logger.error("User declined %s", changetype)
		raise SystemExit
	return "Yes"

def query_mod(slugs):
	if not slugs:
		for file in os.listdir(f"{commons.instance_dir}/.content"):
			if ".mm.toml" in file:
				index = toml.load(f"{commons.instance_dir}/.content/{file}")
				print(file[:-8], index["version"])
				logger.info("Found mod %s", file)
	elif isinstance(slugs, list):
		for slug in slugs:
			if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml")):
				index = toml.load(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"))
				print(f"{slug} {index['version']}")
				logger.info("Found mod %s (%s) version %s (%s)", slug, index['mod-id'], index['version'], index['version-id'])
			else:
				print(f"Mod '{slug}' was not found")
				logger.info("Couldnt find index for mod %s", {slug})
	elif isinstance(slugs, str):
		return os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slugs}.mm.toml"))

def toggle_mod(slugs):
	for slug in slugs:
		index = toml.load(os.path.join(commons.instance_dir, ".content", f"{slugs}.mm.toml"))
		if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], index["filename"])):
			os.rename(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], index['filename']), os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{index['filename']}.disabled"))
			index['filename'] = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{index['filename']}.disabled")
			print(f"Mod '{slug}' has been disabled")
			logger.info("Moved content '%s' from %s to %s", slug, index['filename'], index['filename'] + '.disabled')
		elif os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{index['filename']}.disabled")):
			os.rename(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{index['filename']}.disabled"), os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], index['filename']))
			index['filename'] = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{index['filename']}")
			print(f"Mod '{slug}' has been enabled")
			logger.info("Moved content '%s' from %s.disabled to %s", slug, index['filename'], index['filename'])

def search_mod(query):
	query = " ".join(query)
	logger.info("Getting search data for query '%s'", query)
	query_data = modrinth.search_api(query)
	if not query_data["hits"]:
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return "no results"
	for hit in reversed(query_data["hits"]):
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, commons.minecraft_version, commons.mod_loader)
		print(f"modrinth/{hit['slug']} by {hit['author']} {'[Installed]' if query_mod(hit['slug']) else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgrade_mod(slugs):
	mods = [{'slug': slug} for slug in slugs]
	for mod in mods:
		mod["api_data"] = modrinth.get_api(mod["slug"])
		mod["api_data"]['versions'] = modrinth.parse_api(mod["api_data"])
		if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml")):
			mod["index"] = toml.load(os.path.join(commons.instance_dir, ".content", f"{mod['slug']}.mm.toml"))
			logger.info("Loaded index for mod '%s'", mod["slug"])
		else:
			mod["index"] = {"slug": f"{mod['slug']}","filename": "-", "version": "None", "version-id": "None"}
			logger.info("Created dummy index for mod new '%s'", mod['slug'])

		for i, version in enumerate(reversed(mod["api_data"]["versions"])):
			suffix = "[INSTALLED]" if version['id'] == mod['index']['version-id'] else '[CACHED]' if  os.path.exists(f"{commons.cache_dir}/mods/{version['files'][0]['filename']}.mm.toml") else ''
			print(f"  {len(mod['api_data']['versions']) - i - 1})\tmodrinth/{mod['slug']}\t{version['version_number']}\t{suffix}")

		choice = input(":: Choose version: ")
		try:
			choice = int(choice)
		except ValueError as exc:
			print("Invalid choice")
			raise RuntimeError(f"Invalid choice, could not cast '{choice}' to int") from exc
		if choice >= len(mod["api_data"]['versions']):
			print("Invalid choice")
			raise RuntimeError(f"Invalid choice, '{choice}' larger than '{len(mod['api_data']['versions'])}, list index out of range")
		if mod["api_data"]['versions'][choice]['id'] == mod["index"]['version-id']:
			print("Invalid choice")
			raise RuntimeError("Invalid choice, already installed")

		mod["api_data"]['versions'][0] = mod["api_data"]['versions'][choice]
	confirm(mods, "download")

	for mod in mods:
		modrinth.get_mod(mod['slug'], mod["api_data"]["versions"][0], mod["index"])
		indexing.mcmm(mod['slug'], mod["api_data"]["versions"][0])
		if not os.path.exists(os.path.join(commons.cache_dir, commons.instancecfg["modfolder"], f"{mod['api_data']['versions'][0]['files'][0]['filename']}.mm.toml")):
			print(f"Caching mod '{mod['slug']}'")
			copyfile(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod['api_data']['versions'][0]['files'][0]['filename']), os.path.join(commons.cache_dir, "mods", mod['api_data']['versions'][0]['files'][0]['filename']))
			copyfile(f"{commons.instance_dir}/.content/{mod['slug']}.mm.toml", f"{commons.cache_dir}/mods/{mod['api_data']['versions'][0]['files'][0]['filename']}.mm.toml")
			logger.info("Copied content '%s' to cache", {mod['slug']})
		print(f"Mod '{mod['slug']}' successfully updated")


def clear_cache():
	if commons.args.cc and len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			cache_data = toml.load(f"{commons.cache_dir}/modrinth-api/{file}")
			if time() - cache_data["time"] > commons.config["api-expire"] or ("api-cache-version" in cache_data and cache_data["api-cache-version"] != 2) or ("query-cache-version" in cache_data and cache_data["query-cache-version"] != 0):
				os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
				logger.info("Deleted cache for %s", file.split('.')[0])
				print(f"Deleted api cache for {file.split('.')[0]} (expired)")
	if commons.args.cc == ("api" or "all") and len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return "No clear"
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
			print(f"Deleted api cache for {file.split('.')[0]}")
			logger.info("Deleted api cache for %s (clear all)", file.split('.')[0])
	if commons.args.cc == "all" and len(os.listdir(os.path.join(commons.cache_dir, "mods"))) != 0:
		print("Are you sure you want to clear content cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing content cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return "No clear"
		for file in os.listdir(f"{commons.cache_dir}/mods"):
			if file.endswith(".jar"):
				os.remove(os.path.join(commons.cache_dir, commons.instancecfg["modfolder"], file))
				print(f"Deleted content cache for {file}")
				logger.info("Deleted content cache for %s (clear content cache)", {file})
			elif file.endswith(".toml"):
				os.remove(os.path.join(commons.cache_dir, commons.instancecfg["modfolder"], file))
				print(f"Deleted index cache for {file.split('.')[0]}")
				logger.info("Deleted index cache for %s (clear content cache)", file.split('.')[0])
	print("Finished clearing cache")

def convert_bytes(size):
	for unit in ['B', 'KB', 'MB', 'GB']:
		if -1024 < size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}"

def main():
	operations = {"addbyslug": add_mod, "update": add_mod, "remove": remove_mod, "cc": clear_cache, "query": query_mod, "toggle": toggle_mod, "search": search_mod, "downgrade": downgrade_mod,
		"instance": "" if "instance" not in commons.args else commons.add_instance if commons.args.instance == "add" else commons.sel_instance if commons.args.instance == "select" else commons.del_instance, "version": lambda _: print(commons.__version__)}

	if not commons.args.__dict__:
		print("No operation specified")
		commons.parser.print_help()
		logger.warning("No operation specified")
	else:
		if list(commons.args.__dict__.keys())[0] not in ["instance", "cc"]:
			operations[list(commons.args.__dict__.keys())[0]](list(commons.args.__dict__.values())[0])
		else:
			operations[list(commons.args.__dict__.keys())[0]]()

if __name__ == "__main__":
	try:
		if "instance" not in commons.args:
			if os.path.exists(f"{commons.instance_dir}/mcmodman.lock"):
				print("mcmodman is already running for this instance")
				logger.info("mcmodman.lock file already exists, exiting")
				raise RuntimeError("mcmodman is already running for this instance")

			with open(f"{commons.instance_dir}/mcmodman.lock", "w", encoding="utf-8"):
				logger.info("Setting lock")

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
		raise
	finally:
		if "instance" not in commons.args and os.path.exists(os.path.expanduser(f"{commons.instance_dir}")):
			logger.info("Removing lock")
			os.remove(os.path.expanduser(f"{commons.instance_dir}/mcmodman.lock"))
		logger.info("Exiting")
