"""
main logic, and functions with front-end functionality
"""
from shutil import copyfile
from time import time
import logging, os, toml, commons, modrinth, indexing, instance

logger = logging.getLogger(__name__)

def add_mod(slugs = None, checkeddependencies=[], depinfo={}, fromdep=False):
	if slugs is None:
		slugs = commons.args["slugs"]
		if commons.args["all"]:
			slugs += query_mod()
	if not slugs:
		raise NoTargetsError
	slugs = list(set(slugs))
	mods = [{'slug': slug} for slug in slugs]
	for mod in mods:
		mod["index"] = indexing.get(mod["slug"])

	if not any('index' in d for d in mods):
		print("all mods updated or not found")
		return

	for mod in reversed(mods):
		mod["api_data"] = modrinth.get_api(mod["slug"])
		if isinstance(mod["api_data"], dict):
			logger.info("Successfully got api data for mod '%s'", mod['slug'])
			mod["api_data"]["versions"] = modrinth.parse_api(mod["api_data"])
			if isinstance(mod["api_data"]["versions"], str):
				print(f"No suitable version found for mod '{mod['slug']}'")
				mods.remove(mod)
			if mod["api_data"]["versions"][0]["id"] == mod["index"]["version-id"]:
				print(f"Mod '{mod["slug"]}' already up to date")
				mods.remove(mod)
			if mod["slug"] in commons.config["ignored-mods"]:
				print(f"Mod '{mod["slug"]}' in ignored-mods, skipping")
				mods.remove(mod["slug"])

	checkeddependencies += [mod["api_data"]["id"] for mod in mods]
	depslugs = []
	for mod in mods:
		for dependency in mod["api_data"]["versions"][0]["dependencies"]:
			if dependency["project_id"] not in checkeddependencies:
				dep_api_data = modrinth.get_api(dependency["project_id"], depcheck=True)
				print(f"mod '{mod['slug']}' is dependent on '{dep_api_data['slug']}' ({'optional' if dependency['dependency_type'] == 'optional' else 'required'})")
				checkeddependencies.append(dependency["project_id"])
				if dependency['dependency_type'] != 'optional' or commons.config["get-optional-dependencies"]:
					depinfo[dep_api_data["slug"]] = 'optional' if dependency['dependency_type'] == 'optional' else 'dependency'
					print(depinfo)
					depslugs.append(dep_api_data["slug"])

	if depslugs and not commons.args["all"] and not commons.args["explicit"]:
		add_mod(slugs=depslugs, checkeddependencies=checkeddependencies, depinfo=depinfo, fromdep=True)

	if not mods:
		print("all mods up to date\n" if not fromdep else "", end="")
		return

	if not commons.args["auto-confirm"]:
		confirm(mods, "download")

	for mod in mods:
		_, folder = modrinth.project_get_type(mod["api_data"])
		modrinth.get_mod(mod["slug"], mod["api_data"], mod["index"])
		logger.info("Sucessfully downloaded content '%s' (%s B)", mod['slug'], mod['api_data']['versions'][0]['files'][0]['size'])
		indexing.mcmm(mod['slug'], mod['api_data'], "explicit" if not fromdep else depinfo[mod['slug']])
		if not os.path.exists(os.path.join(commons.cache_dir, "mods", f"{mod['api_data']['versions'][0]['files'][0]['filename']}")):
			print(f"Caching mod '{mod['slug']}'")
			copyfile(os.path.join(commons.instance_dir, folder, mod['api_data']['versions'][0]['files'][0]['filename']), os.path.join(commons.cache_dir, "mods", mod['api_data']['versions'][0]['files'][0]['filename']))
			logger.info("Copied content '%s' to cache", {mod['slug']})
		print(f"Mod '{mod['slug']}' successfully updated")

def remove_mod():
	slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [{'slug': slug} for slug in slugs]
	for mod in reversed(mods):
		mod["index"] = indexing.get(mod["slug"])
		if mod["index"] is None:
			print(f"Mod '{mod['slug']}' is not installed")
			logger.error("Could not load index '%s' because it is not installed", {mod['slug']})
			mods.remove(mod)
		if mod["slug"] in commons.config["ignored-mods"]:
			commons.config["ignored-mods"].remove(mod["slug"])

	if not mods:
		print("no mods found")
		return

	if not commons.args["auto-confirm"]:
		confirm(mods, "remove")

	for mod in mods:
		os.remove(f"{commons.instance_dir}/.content/{mod['slug']}.mm.toml")
		os.remove(os.path.join(commons.instance_dir, mod["index"]["folder"], mod['index']['filename']))
		logger.info("Removed content '%s'", {mod['slug']})
		if "index-compatibility" in commons.instancecfg:
			os.remove(os.path.join(commons.instance_dir, mod["index"]["folder"], ".index", f"{mod['slug']}.pw.toml"))
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

def query_mod(slugs=None):
	slugs = commons.args["slugs"] if slugs is None else slugs
	if not slugs:
		installed = []
		for file in os.listdir(f"{commons.instance_dir}/.content"):
			if ".mm.toml" in file:
				index = indexing.get(file[:-8])
				if commons.args["all"]:
					pass
				elif commons.args["explicit"] and not index["reason"] == "explicit":
					continue
				elif commons.args["depedency"] and not index["reason"] == "dependency":
					continue
				elif commons.args["optional"] and not index["reason"] == "optional":
					continue
				if commons.args["operation"] == "query":
					print(index["slug"], index["version"])
				logger.info("Found mod %s", file)
				installed.append(index["slug"])
		return installed
	if isinstance(slugs, list):
		for slug in slugs:
			if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml")):
				index = toml.load(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"))
				print(f"{slug} {index['version']}")
				logger.info("Found mod %s (%s) version %s (%s)", slug, index['mod-id'], index['version'], index['version-id'])
				if len(slugs) == 1:
					return True
			else:
				print(f"Mod '{slug}' was not found")
				logger.info("Couldnt find index for mod %s", {slug})
				if len(slugs) == 1:
					return False
	return None

def toggle_mod():
	slugs = commons.args["slugs"]
	for slug in slugs:
		index = indexing.get(slug)
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

def search_mod():
	query = commons.args["query"]
	logger.info("Getting search data for query '%s'", query)
	query_data = modrinth.search_api(query)
	if not query_data["hits"]:
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return
	for hit in reversed(query_data["hits"]):
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, commons.minecraft_version, commons.mod_loader)
		print(f"modrinth/{hit['slug']} by {hit['author']} {'[Installed]' if query_mod(hit['slug']) else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgrade_mod():
	slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [{'slug': slug} for slug in slugs]
	for mod in mods:
		mod["api_data"] = modrinth.get_api(mod["slug"])
		mod["api_data"]['versions'] = modrinth.parse_api(mod["api_data"])
		mod["index"] = indexing.get(mod["slug"])

		for i, version in enumerate(reversed(mod["api_data"]["versions"])):
			suffix = "[INSTALLED]" if version['id'] == mod['index']['version-id'] else '[CACHED]' if os.path.exists(os.path.join(commons.cache_dir, "mods", f"{version['files'][0]['filename']}")) else ''
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

	if not commons.args["auto-confirm"]:
		confirm(mods, "download")

	for mod in mods:
		ignore = input(f":: add {mod["slug"]} to ignored-packages? [y/N]: ")
		if ignore.lower() == "y":
			commons.config["ignored-mods"].append(mod["slug"])

		_, folder = modrinth.project_get_type(mod["api_data"])
		modrinth.get_mod(mod['slug'], mod["api_data"], mod["index"])
		indexing.mcmm(mod['slug'], mod["api_data"])
		if not os.path.exists(os.path.join(commons.cache_dir, "mods", f"{mod['api_data']['versions'][0]['files'][0]['filename']}")):
			print(f"Caching mod '{mod['slug']}'")
			copyfile(os.path.join(commons.instance_dir, folder, mod['api_data']['versions'][0]['files'][0]['filename']), os.path.join(commons.cache_dir, "mods", mod['api_data']['versions'][0]['files'][0]['filename']))
			logger.info("Copied content '%s' to cache", {mod['slug']})
		print(f"Mod '{mod['slug']}' successfully updated")

	with open(os.path.join(commons.config_dir, "config.toml"), "w") as f:
		toml.dump(commons.config, f)

def clear_cache():
	if len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			cache_data = toml.load(f"{commons.cache_dir}/modrinth-api/{file}")
			if time() - cache_data["time"] > commons.config["api-expire"] or ("api-cache-version" in cache_data and cache_data["api-cache-version"] != 2) or ("query-cache-version" in cache_data and cache_data["query-cache-version"] != 0):
				os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
				logger.info("Deleted cache for %s", file.split('.')[0])
				print(f"Deleted api cache for {file.split('.')[0]} (expired)")
	if commons.args["suboperation"] == ("api" or "all") and len(os.listdir(f'{commons.cache_dir}/modrinth-api')) != 0:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return
		for file in os.listdir(f"{commons.cache_dir}/modrinth-api"):
			os.remove(f"{commons.cache_dir}/modrinth-api/{file}")
			print(f"Deleted api cache for {file.split('.')[0]}")
			logger.info("Deleted api cache for %s (clear all)", file.split('.')[0])
	if commons.args["suboperation"] == "all" and len(os.listdir(os.path.join(commons.cache_dir, "mods"))) != 0:
		print("Are you sure you want to clear content cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing content cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return
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

class LockExistsError(Exception):
	"error: could not lock instance: File Exists"
class NoTargetsError(Exception):
	"error: no targets specified"

def main():
	operations = {"sync": add_mod, "update": add_mod, "remove": remove_mod, "clear-cache": clear_cache, "query": query_mod, "toggle": toggle_mod, "search": search_mod, "downgrade": downgrade_mod,
		"instance": instance.instance_meta, "version": lambda _: print(commons.__version__)}

	operations[commons.args["operation"]]()

if __name__ == "__main__":
	try:
		if commons.args["lock"]:
			if os.path.exists(f"{commons.instance_dir}/mcmodman.lock"):
				print("mcmodman is already running for this instance")
				logger.info("mcmodman.lock file already exists, exiting")
				raise LockExistsError("mcmodman is already running for this instance")

			with open(f"{commons.instance_dir}/mcmodman.lock", "w", encoding="utf-8"):
				logger.info("Setting lock")

		main()
	except KeyboardInterrupt:
		print("Interrupt signal received")
		logger.info("Process interrupted by user")
	except LockExistsError:
		print(f"error: could not lock instance: File Exists\n\tIf you're sure mcmodman is not already running for this instance, you can remove {commons.instance_dir}/mcmodman.lock")
		logger.critical("already running for instance")
		raise SystemExit
	except NoTargetsError:
		print(f"error: no targets specified")
		logger.critical("already running for instance")
	except RuntimeError as e:
		print("An error occurred while running mcmodman")
		logger.critical(e)
	except Exception as e:
		print("An unexpected error occured")
		logger.critical(e)
		raise
	finally:
		if commons.args["lock"] and os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "mcmodman.lock"))):
			logger.info("Removing lock")
			os.remove(os.path.expanduser(os.path.join(commons.instance_dir, "mcmodman.lock")))
		logger.info("Exiting")
