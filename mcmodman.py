"""
main logic, and functions with front-end functionality
"""

import logging, os, toml, cache, commons, modrinth, indexing, instance, local

logger = logging.getLogger(__name__)

def addMod(slugs = None, checkeddependencies=[], reasons={}, fromdep=False):
	if slugs is None:
		slugs = commons.args["slugs"]
		if commons.args["all"]:
			slugs += queryMod()
	if not slugs:
		raise NoTargetsError
	slugs = list(set(slugs))
	mods = [{'slug': slug} for slug in slugs]
	for mod in reversed(mods):
		if mod["slug"] in commons.config["ignored-mods"]:
			print(f"Mod '{mod["slug"]}' in ignored-mods, skipping")
			mods.remove(mod)
		if mod["slug"] not in reasons and mod["slug"] in commons.args["slugs"]:
			reasons[mod["slug"]] = "explicit"
		mod["source"] = "local" if any(ext in mod["slug"] for ext in (".jar", ".zip")) else "modrinth"
		mod["index"] = indexing.get(mod["slug"], reason=reasons[mod["slug"]])
		if mod["index"].get("source") != None:
			mod["source"] = mod["index"]["source"]

	if not any('index' in d for d in mods):
		print("all mods updated or not found")
		return

	for mod in reversed(mods):
		mod["api_data"] = sources[mod["source"]].getAPI(mod["slug"])
		if isinstance(mod["api_data"], dict):
			logger.info("Successfully got api data for mod '%s'", mod['slug'])
			mod["api_data"]["versions"] = sources[mod["source"]].parseAPI(mod["api_data"])
			if mod["source"] == "local":
				mod["slug"] = mod["api_data"]["versions"][0]["slug"]
				mod["index"] = indexing.get(mod["slug"])
			if "disabled" in mod["index"]["filename"]:
				print(f"mod '{mod["slug"]}' is diabled, skipping")
				mods.remove(mod)
			if isinstance(mod["api_data"]["versions"], str):
				print(f"No suitable version found for mod '{mod['slug']}'")
				mods.remove(mod)
			elif mod["api_data"]["versions"][0]["id"] == mod["index"]["version-id"]:
				print(f"Mod '{mod["slug"]}' already up to date")
				mods.remove(mod)

	checkeddependencies += [mod["api_data"]["id"] for mod in mods]
	depslugs = []
	for mod in mods:
		for dependency in mod["api_data"]["versions"][0]["dependencies"]:
			if dependency["project_id"] not in checkeddependencies:
				dep_api_data = sources[mod["source"]].getAPI(dependency["project_id"], depcheck=True)
				reasons[dep_api_data["slug"]] = 'optional' if dependency['dependency_type'] == 'optional' else 'dependency'
				print(f"mod '{mod['slug']}' is dependent on '{dep_api_data['slug']}' ({"required" if reasons[dep_api_data["slug"]] == "dependency" else reasons[dep_api_data["slug"]]})")
				checkeddependencies.append(dependency["project_id"])
				if dependency['dependency_type'] != 'optional' or commons.config["get-optional-dependencies"]:
					depslugs.append(dep_api_data["slug"])

	if depslugs and not commons.args["all"] and not commons.args["explicit"]:
		addMod(slugs=depslugs, checkeddependencies=checkeddependencies, reasons=reasons, fromdep=True)

	if not mods:
		print("all mods up to date\n" if not fromdep else "", end="")
		return

	if not commons.args["auto-confirm"]:
		confirm(mods, "download")

	for mod in mods:
		if queryMod([mod["slug"]]):
			removeMod([mod["slug"]], fromadd=True)
		if mod["slug"] == "cardboard":
			commons.instancecfg["translation-layer"] = "cardboard"
			with open(f"{commons.instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		if mod["slug"] in ["connector", "forgified-fabric-api"]:
			commons.instancecfg["translation-layer"] = "sinytra"
			with open(f"{commons.instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		sources[mod["source"]].getMod(mod["slug"], mod["api_data"], mod["index"])
		logger.info("Sucessfully downloaded content '%s' (%s B)", mod['slug'], mod['api_data']['versions'][0]['files'][0]['size'])
		indexing.mcmm(mod['slug'], mod['api_data'], mod['index']['reason'], mod["source"])

def removeMod(slugs=None, fromadd=False):
	if slugs is None:
		slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [{'slug': slug} for slug in slugs]
	for mod in reversed(mods):
		mod["index"] = indexing.get(mod["slug"])
		if mod["index"] is None or mod["index"]["version"] == "None":
			print(f"Mod '{mod['slug']}' is not installed")
			logger.error("Could not load index '%s' because it is not installed", {mod['slug']})
			mods.remove(mod)
		if mod["slug"] in commons.config["ignored-mods"]:
			commons.config["ignored-mods"].remove(mod)

	if not mods:
		print("no mods found")
		return

	if not commons.args["auto-confirm"] and not fromadd:
		confirm(mods, "remove")

	for mod in mods:
		if mod["slug"] in ["cardboard", "connector"]:
			commons.instancecfg["translation-layer"] = "None"
			with open(f"{commons.instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		os.remove(f"{commons.instance_dir}/.content/{mod['slug']}.mm.toml")
		os.remove(os.path.join(mod["index"]["folder"], mod["index"]["filename"]))
		logger.info("Removed content '%s'", {mod['slug']})
		if "index-compatibility" in commons.instancecfg:
			os.remove(os.path.join(mod["index"]["folder"], ".index", f"{mod['slug']}.pw.toml"))
		if not fromadd:
			print(f"Removed mod '{mod['slug']}'")

def confirm(mods, changetype):
	print("")
	totaloldsize = sum(os.path.getsize(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod["index"]["filename"])) for mod in mods if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod["index"]["filename"])))
	totalnewsize = sum(mod["api_data"]["versions"][0]["files"][0]["size"] for mod in mods) if changetype == "download" else 0

	for mod in mods:
		print(f"Mod {mod["source"]}/{mod['slug']} {mod['index']['version']} --> {mod['api_data']['versions'][0]['version_number'] if changetype == 'download' else None}")
	print(f"\nTotal {changetype} size: {convertBytes(totalnewsize if changetype == 'download' else totaloldsize)}")
	print(f"Net upgrade Size: {convertBytes(totalnewsize - totaloldsize)}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		logger.error("User declined %s", changetype)
		raise SystemExit

def queryMod(slugs=None):
	slugs = commons.args["slugs"] if slugs is None else slugs
	if not slugs:
		installed = []
		for file in os.listdir(f"{commons.instance_dir}/.content"):
			if ".mm.toml" in file:
				index = indexing.get(file[:-8])
				if commons.args["all"]:
					pass
				elif (commons.args["explicit"] and index["reason"] != "explicit") or (commons.args["depedency"] and index["reason"] != "dependency") or (commons.args["optional"] and index["reason"] != "optional"):
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
				if commons.args["operation"] == "query":
					print(f"Mod '{slug}' was not found")
				logger.info("Couldnt find index for mod %s", {slug})
				if len(slugs) == 1:
					return False
	return None

def toggleMod():
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
		else:
			raise TargetNotFoundError

def searchMod():
	query = commons.args["query"]
	logger.info("Getting search data for query '%s'", query)
	query_data = modrinth.searchAPI(query)
	if not query_data["hits"]:
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return
	for hit in reversed(query_data["hits"]):
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, commons.minecraft_version, commons.mod_loader)
		print(f"modrinth/{hit['slug']} by {hit['author']} {'[Installed]' if queryMod(hit['slug']) else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgradeMod():
	slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [{'slug': slug} for slug in slugs]
	for mod in mods:
		mod["api_data"] = modrinth.getAPI(mod["slug"])
		mod["api_data"]['versions'] = modrinth.parseAPI(mod["api_data"])
		mod["index"] = indexing.get(mod["slug"])

		for i, version in enumerate(reversed(mod["api_data"]["versions"])):
			suffix = "[INSTALLED]" if version['id'] == mod['index']['version-id'] else '[CACHED]' if cache.isModCached(version['files'][0]['filename']) else ''
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
		
		if queryMod([mod["slug"]]):
			removeMod([mod["slug"]], fromadd=True)
		if mod["slug"] == "cardboard":
			commons.instancecfg["translation-layer"] = "cardboard"
			with open(f"{commons.instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
			if not os.path.exists(os.path.join(commons.instance_dir, "plugins")):
				os.makedirs(os.path.join(commons.instance_dir, "plugins"))
		if mod["slug"] in ["connector", "forgified-fabric-api"]:
			commons.instancecfg["translation-layer"] = "sinytra"
			with open(f"{commons.instance_dir}/mcmodman_managed.toml", "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)

		_, folder = modrinth.projectGetType(mod["api_data"])
		modrinth.getMod(mod['slug'], mod["api_data"], mod["index"])
		indexing.mcmm(mod['slug'], mod["api_data"], mod["index"]["reason"], "modrinth")
		cache.setModCache(mod['api_data']['versions'][0]['files'][0]['filename'], folder)
		print(f"Mod '{mod['slug']}' successfully updated")

	with open(os.path.join(commons.config_dir, "config.toml"), "w", encoding="utf-8") as f:
		toml.dump(commons.config, f)

def convertBytes(size):
	for unit in ['B', 'KB', 'MB', 'GB']:
		if -1024 < size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}"

class LockExistsError(Exception):
	"error: could not lock instance: File Exists"
class NoTargetsError(Exception):
	"error: no targets specified"
class TargetNotFoundError(Exception):
	"error: no targets specified"

def main():
	operations = {"sync": addMod, "update": addMod, "remove": removeMod, "clear-cache": cache.clearCache, "query": queryMod, "toggle": toggleMod, "search": searchMod, "downgrade": downgradeMod,
		"instance": instance.instanceMeta, "version": lambda _: print(commons.__version__)}

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

		sources = {"local": local, "modrinth": modrinth}

		main()
	except local.zipfile.BadZipFile:
		print("bad")
	except KeyboardInterrupt:
		print("Interrupt signal received")
		logger.info("Process interrupted by user")
	except LockExistsError as e:
		print(f"error: could not lock instance: File Exists\n\tIf you're sure mcmodman is not already running for this instance, you can remove {commons.instance_dir}/mcmodman.lock")
		logger.critical("already running for instance")
		raise SystemExit from e
	except NoTargetsError:
		print("error: no targets specified")
		logger.critical("already running for instance")
	except RuntimeError as e:
		print("An error occurred while running mcmodman")
		logger.critical(e)
		raise
	except Exception as e:
		print("An unexpected error occured", e)
		logger.critical(e)
		raise
	finally:
		if commons.args["lock"] and os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, "mcmodman.lock"))):
			logger.info("Removing lock")
			os.remove(os.path.expanduser(os.path.join(commons.instance_dir, "mcmodman.lock")))
		logger.info("Exiting")
		#raise SystemExit
