"""
main logic, and functions with front-end functionality
"""

import logging, os, toml, cache, commons, hangar, modrinth, indexing, instance, local
from typing import List # DEBUG

logger = logging.getLogger(__name__)

class ModType():
	def __init__(self, slug: str, reason: str="explicit"):
		self.slug = slug
		self.api_data = {}
		self.index = indexing.get(slug, reason)
		if self.index is None:
			raise TargetNotFoundError(slug)
		if self.index.get("source") is not None:
			self.source = self.index["source"]
		else:
			self.source = "local" if any(ext in self.slug for ext in (".jar", ".zip")) else "sourceagnostic"
	
	def isIgnored(self) -> bool:
		return self.slug in commons.config["ignored-mods"]

	def isDisabled(self) -> bool | None: # returns true if disabled, false if enabled and none if not installed
		return True if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index['filename']}.disabled")) else False if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index['filename']}")) else None
	
	def isInstalled(self) -> bool:
		return self.index["version"] != "None"
	
	def toggle(self):
		if self.index["version"] == "None": # if not installed, raise target not found
			raise TargetNotFoundError(self.slug)
		if self.isDisabled():
			currentpath, newpath = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index['filename']}.disabled"), os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index["filename"]}")
			self.index['filename'] = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index['filename']}")
		else:
			currentpath, newpath = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index["filename"]}"), os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index["filename"]}.disabled")
			self.index['filename'] = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"{self.index['filename']}.disabled")
		logger.info("Moved content '%s' from %s to %s", self.slug, os.path.basename(currentpath), os.path.basename(newpath))
		os.rename(currentpath, newpath)
		print(f"Mod '{self.slug}' has been {'enabled' if self.isDisabled() else 'disabled'}")
		with open(os.path.join(commons.instance_dir, ".content", f"{self.slug}.mm.toml"), "w", encoding="utf-8") as f:
			toml.dump(self.index, f)

def addMod(): # TODO: merge refactored functions into their original places
	slugs = commons.args["slugs"]
	if commons.args["all"]:
		slugs.extend(queryMod())
	if not slugs:
		raise NoTargetsError
	slugs = list(set(slugs))
	mods: List[ModType] = [ModType(slug) for slug in slugs if slug not in commons.config["ignored-mods"]]

	i, toremove, checked = -1, [], []
	while i < len(mods) - 1:
		i += 1 
		mod = mods[i]
		mod.api_data = sources[mod.source].getAPI(mod.slug)
		mod.source = mod.api_data["source"]
		if not isinstance(mod.api_data, dict):
			continue
		logger.info("Successfully got api data for mod '%s'", mod.slug)
		mod.api_data["versions"] = sources[mod.source].parseAPI(mod.api_data)
		checked.extend([mod.slug, mod.api_data["id"]])
		if mod.source == "local":
			mod.slug = mod.api_data["versions"][0]["slug"]
			mod.index = indexing.get(mod.slug)
		if mod.isDisabled():
			print(f"mod '{mod.slug}' is disabled, skipping")
			toremove.append(mod)
			continue
		if isinstance(mod.api_data["versions"], str):
			print(f"No suitable version found for mod '{mod['slug']}'")
			toremove.append(mod)
			continue
		elif mod.api_data["versions"][0]["id"] == mod.index["version-id"]:
			print(f"Mod '{mod.slug}' already up to date, {'skipping' if commons.args["operation"] == "upgrade" or mod.slug not in commons.args["slugs"] else 'reinstalling'}")
			if commons.args["operation"] == "upgrade" or mod.slug not in commons.args["slugs"]:
				toremove.append(mod)
				continue
		for dependency in mod.api_data["versions"][0]["dependencies"]:
			if dependency["project_id"] not in checked:
				continue
			dep_api_data = sources[mod.source].getAPI(dependency["project_id"], depcheck=True)
			reason = 'optional' if dependency['dependency_type'] == 'optional' else 'dependency'
			print(f"mod '{mod.slug}' is dependent on '{dep_api_data['slug']}' ({"required" if reason == "dependency" else reason})")
			checked.append(dependency["project_id"])
			if dependency['dependency_type'] != 'optional' or commons.config["get-optional-dependencies"] or commons.args["optional"]:
				mods.append(ModType(dep_api_data['slug'], reason))

	for mod in toremove:
		mods.remove(mod)
	if not mods:
		print("all mods are up to date")
		return

	_ = "" if commons.args["noconfirm"] else confirm(mods)

	for mod in mods:
		_ = removeMod([mod.slug]) if mod.isInstalled() else ""
		if mod.slug in ["connector", "cardboard"] and commons.instancecfg["translation-layer"] == "None":
			commons.instancecfg["translation-layer"] = "sinytra" if mod.slug == "connector" else "cardboard"
			with open(os.path.join(commons.instance_dir, "mcmodman_managed.toml"), "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		sources[mod.source].getMod(mod.slug, mod.api_data)
		logger.info("Sucessfully downloaded content '%s' (%s B)", mod.slug, mod.api_data['versions'][0]['files'][0]['size'])
		indexing.mcmm(mod.slug, mod.api_data, mod.index['reason'], mod.source)

def removeMod(slugs=None):
	if slugs is None:
		slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]

	if all(not mod.isInstalled() for mod in mods):
		print("no mods found")
		return
	for mod in mods:
		if not mod.isInstalled():
			raise TargetNotFoundError(mod.slug)

	_ = "" if commons.args["noconfirm"] or commons.args["operation"] != "remove" else confirm(mods)

	for mod in mods:
		if mod.slug in ("cardboard", "connector"):
			commons.instancecfg["translation-layer"] = "None"
			with open(os.path.join(commons.instance_dir, "mcmodman_managed.toml"), "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		os.remove(os.path.join(commons.instance_dir, ".content", f"{mod.slug}.mm.toml"))
		if os.path.exists(os.path.join(mod.index["folder"], mod.index["filename"])):
			os.remove(os.path.join(mod.index["folder"], mod.index["filename"]))
		logger.info("Removed content '%s'", mod.slug)
		if "index-compatibility" in commons.instancecfg and os.path.exists(os.path.join(mod.index["folder"], ".index", f"{mod.slug}.pw.toml")):
			os.remove(os.path.join(mod.index["folder"], ".index", f"{mod.slug}.pw.toml"))
		print(f"Removed mod '{mod.slug}'\n" if commons.args["operation"] == "remove" else "", end='')

def confirm(mods: List[ModType]):
	print("")
	op = "remove" if commons.args["operation"] == "remove" else "download"
	totaloldsize = sum(os.path.getsize(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod.index["filename"])) for mod in mods if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod.index["filename"])))
	totalnewsize = sum(mod.api_data["versions"][0]["files"][0]["size"] for mod in mods) if op == "download"  else 0

	for mod in mods:
		print(f"Mod {mod.source}/{mod.slug} {mod.index['version']} --> {mod.api_data['versions'][0]['version_number'] if op == "download"  else None}")
	print(f"\nTotal {op} size: {convertBytes(totalnewsize if op == "download" else totaloldsize)}")
	print(f"Net upgrade Size: {convertBytes(totalnewsize - totaloldsize)}")
	yn = input("\n:: Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() != 'y' and yn != '':
		logger.error("User declined %s", op)
		raise SystemExit

def queryMod(slugs=None):
	slugs = None if commons.args["all"] else commons.args["slugs"] if slugs is None else slugs
	if not slugs:
		installed = []
		for file in os.listdir(os.path.join(commons.instance_dir, ".content")):
			if ".mm.toml" in file:
				index = indexing.get(file[:-8])
				if commons.args["all"]:
					pass
				elif (commons.args["explicit"] and index["reason"] != "explicit") or (commons.args["dependency"] and index["reason"] != "dependency") or (commons.args["optional"] and index["reason"] != "optional"):
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
				logger.info("Found mod %s (%s) version %s (%s)", slug, index.get("mod-id"), index['version'], index['version-id'])
			else:
				if commons.args["operation"] == "query":
					print(f"Mod '{slug}' was not found")
				logger.info("Couldnt find index for mod %s", {slug})
	return None

def toggleMod():
	slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]
	for mod in mods:
		mod.toggle()

def searchMod():
	query = commons.args["query"]
	logger.info("Getting search data for query '%s'", query)
	queryData = {source: sources[source].searchAPI for source in sources if "SEARCH" in sources[source].TAGS}
	queryData = {"modrinth": modrinth.searchAPI(query), "hangar": hangar.searchAPI(query)}
	if not queryData["modrinth"]["hits"] and not queryData["hangar"]["hits"]:
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return
	queryData["all"] = queryData["modrinth"]["hits"]
	queryData["all"].extend(queryData["hangar"]["hits"])
	queryData["all"].sort(key=lambda x: x["downloads"])
	for hit in queryData["all"]:
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, commons.minecraft_version, commons.mod_loader)
		print(f"{hit['source']}/{hit['slug']} by {hit['author']} {'[Installed]' if queryMod(hit['slug']) else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgradeMod():
	slugs = commons.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]
	for mod in mods:
		versions = []
		mod.api_data = {source: sources[source].getAPI(mod.slug) for source in sources if "EXTERNAL" in sources[source].TAGS}
		for source in [source for source in sources if "EXTERNAL" in sources[source].TAGS]:
			if isinstance(mod.api_data[source], str):
				continue
			mod.api_data[source]["versions"] = sources[source].parseAPI(mod.api_data[source]) 
			if isinstance(mod.api_data[source].get("versions"), str):
				continue
			if not versions:
				mod.api_data["type"] = mod.api_data[source]["project_type"]
			versions.extend(mod.api_data[source]["versions"])
		for version in versions:
			version["date"] = version["date_published"] or version["createdAt"] 
		mod.api_data["versions"] = sorted(versions, key=lambda x: x['date'], reverse=True)

		for i, version in enumerate(reversed(mod.api_data["versions"])):
			suffix = "[INSTALLED]" if version['id'] == mod.index['version-id'] else '[CACHED]' if cache.isModCached(mod.slug, commons.mod_loader, version['version_number'], commons.minecraft_version) else ''
			print(f"  {len(mod.api_data['versions']) - i - 1})\t{version["source"]}/{mod.slug}\t{version['version_number']}\t{suffix}")

		choice = input(":: Choose version: ")
		try:
			choice = int(choice)
		except ValueError as exc:
			raise InvalidChoice(f"Invalid choice, could not cast '{choice}' to int") from exc
		if choice < 0 or choice >= len(mod.api_data["versions"]):
			raise InvalidChoice(f"Invalid choice, '{choice}' larger than '{len(mod.api_data['versions']) - 1}', list index out of range")
		if mod.api_data["versions"][choice]["id"] == mod.index["version-id"]:
			raise InvalidChoice("Invalid choice, the selected version is already installed")
		
		mod.api_data['versions'][0] = mod.api_data['versions'][choice]
		mod.source = mod.api_data['versions'][0]["source"]
	
	_ = "" if commons.args["noconfirm"] else confirm(mods)

	toignore = []
	for mod in mods:
		ignore =  input(f":: add {mod.slug} to ignored-packages? [y/N]: ").lower()
		if ignore == "y":
			toignore.append(mod.slug)
		_ = removeMod([mod.slug]) if mod.isInstalled() else ""
		if mod.slug in ["connector", "cardboard"]:
			commons.instancecfg["translation-layer"] = "sinytra" if mod.slug == "connector" else "cardboard"
			with open(os.path.join(commons.instance_dir, "mcmodman_managed.toml"), "w", encoding="utf-8") as f:
				toml.dump(commons.instancecfg, f)
		
		sources[mod.api_data["versions"][0].get("source", "modrinth")].getMod(mod.slug, mod.api_data)
		indexing.mcmm(mod.slug, mod.api_data, mod.index["reason"], mod.api_data["versions"][0]["source"])
		cache.setModCache(mod.slug, commons.mod_loader, mod.api_data["versions"][0]['version_number'], commons.minecraft_version, mod.api_data["versions"][0]["folder"], mod.api_data["versions"][0]['files'][0]['filename'])
		print(f"Mod '{mod.slug}' successfully updated")
	
	ignoreMod(toignore)

def ignoreMod(slugs=None):
	slugs = commons.args["slugs"] if slugs is None else slugs
	for slug in slugs:
		commons.config["ignored-mods"].append(slug)
	commons.config["ignored-mods"] = list(set(commons.config["ignored-mods"]))

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
class NoValidVersions(Exception):
	"error: could not find any valid versions"
class NoTargetsError(Exception):
	"error: no targets specified"
class TargetNotFoundError(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)
class InvalidChoice(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)

class sourceagnostic:
	TAGS = []
	@staticmethod
	def getAPI(slug):
		apiData = {"modrinth": modrinth.getAPI(slug), "hangar": hangar.getAPI(slug)}
		toremove = [source for source in apiData if not isinstance(apiData[source], dict)]
		for source in toremove:
			del apiData[source]
		if not apiData:
			raise TargetNotFoundError(slug)
		if isinstance(apiData.get("modrinth"), dict) and isinstance(apiData.get("hangar"), dict):
			print(f"found multiple sources for mod '{slug}'\n")
			for i, source in enumerate(reversed(apiData)):
				print(f"  {len(apiData) - i - 1})\t{source}/{slug}")
			choice = input("\n:: Choose source: ")
			try:
				choice = int(choice)
			except ValueError as exc:
				print("Invalid choice")
				raise InvalidChoice(f"Invalid choice, could not cast '{choice}' to int") from exc
			if 0 > choice >= len(apiData):
				print("Invalid choice")
				raise InvalidChoice(f"Invalid choice, '{choice}' larger than '{len(apiData)}', list index out of range")
			return list(apiData.values())[choice]
		for s in apiData:
			if isinstance(apiData[s], dict):
				return apiData[s]

if __name__ == "__main__":
	try:
		if commons.args["lock"]:
			try:
				fd = os.open(os.path.join(commons.instance_dir, "mcmodman.lock"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
				with os.fdopen(fd, 'w', encoding='utf-8') as f:
					logger.info("Setting lock")
			except FileExistsError:
				print("mcmodman is already running for this instance")
				logger.info("mcmodman.lock file already exists, exiting")
				raise LockExistsError("mcmodman is already running for this instance")

		sources = {"local": local, "modrinth": modrinth, "hangar": hangar, "sourceagnostic": sourceagnostic}

		operations = {"sync": addMod, "upgrade": addMod, "remove": removeMod, "clear-cache": cache.clearCache, "query": queryMod, "toggle": toggleMod, "search": searchMod, "downgrade": downgradeMod,
		"instance": instance.instanceMeta, "ignore": ignoreMod, "version": lambda: print(commons.__version__)}
		operations[commons.args["operation"]]()
	except local.zipfile.BadZipFile:
		print("bad")
	except KeyboardInterrupt:
		print("Interrupt signal received")
		logger.info("Process interrupted by user")
	except LockExistsError as e:
		print(f"error: could not lock instance: File Exists\n\tIf you're sure mcmodman is not already running for this instance, you can remove {commons.instance_dir}/mcmodman.lock")
		logger.critical("already running for instance")
		raise SystemExit from e
	except InvalidChoice as e:
		print(f"error: {e}")
	except NoValidVersions:
		print("error: could not find any valid versions")
	except NoTargetsError:
		print("error: no targets specified")
		logger.critical("user called operation that takes targets but no targets given")
	except TargetNotFoundError as e:
		print(f"error: target not found: {e}")
		logger.critical("user gave target that doesnt exist")
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
