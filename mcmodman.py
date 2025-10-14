"""
main logic, and functions with front-end functionality
"""
import logging, os, commons, cache, indexing, instance
from typing import List, Protocol
ctx = commons.ctx

if not os.path.exists(os.path.join(ctx.config["cache-dir"], "modrinth-api")): # ts will not make it to version 3
	os.makedirs(os.path.join(ctx.config["cache-dir"], "modrinth-api"))
if not os.path.exists(os.path.join(ctx.config["cache-dir"], "hangar-api")):
	os.makedirs(os.path.join(ctx.config["cache-dir"], "hangar-api"))

logger = logging.getLogger(__name__)

class ModType():
	def __init__(self, slug: str, reason: str="explicit"):
		self.slug = slug
		self.api_data = {}
		self.index: dict = indexing.get(ctx, slug, "explicit" if ctx.args["asexplicit"] else "dependency" if ctx.args["asdeps"] else reason)
		if self.index is None:
			raise TargetNotFoundError(slug)
		if self.index.get("source") is not None:
			self.source = self.index["source"]
		elif "/" in slug:
			for source in [source for source in sources if hasattr(sources[source], "BANG")]:
				if not slug.startswith(f"{sources[source].BANG}/"):
					continue
				self.source = source
				self.slug = slug[len(f"{sources[source].BANG}/"):]
				break
		else:
			self.source = "local" if any(self.slug.endswith(ext) for ext in (".jar", ".zip")) else "sourceagnostic"

	def isIgnored(self) -> bool:
		return self.slug in ctx.config["ignored-mods"]

	def isDisabled(self) -> bool | None: # returns true if disabled, false if enabled and none if not installed
		if self.index["index-version"] <= 4:
			return True if os.path.exists(os.path.join(self.index["folder"], f"{self.index['filename']}.disabled")) else False if os.path.exists(os.path.join(self.index["folder"], f"{self.index['filename']}")) else None
		else:
			return True if os.path.exists(os.path.join(f"{self.index['files'][0]}.disabled")) else False if os.path.exists(self.index['files'][0]) else None

	def isInstalled(self) -> bool:
		return self.index["version"] != "None"

	def getPath(self) -> str:
		if self.index["index-version"] <= 4:
			return os.path.join(ctx.instanceDir, os.path.basename(self.index["folder"]), self.index["filename"])
		else:
			return self.index["files"]

	def toggle(self):
		if self.index["version"] == "None": # if not installed, raise target not found
			raise TargetNotFoundError(self.slug)
		if self.isDisabled():
			currentpath, newpath = os.path.join(ctx.instanceDir, ctx.instance["modfolder"], f"{self.index['filename']}.disabled"), os.path.join(ctx.instanceDir, ctx.instance["modfolder"], f"{self.index['filename']}")
		else:
			currentpath, newpath = os.path.join(ctx.instanceDir, ctx.instance["modfolder"], f"{self.index['filename']}"), os.path.join(ctx.instanceDir, ctx.instance["modfolder"], f"{self.index['filename']}.disabled")
		logger.info("Moved content '%s' from %s to %s", self.slug, os.path.basename(currentpath), os.path.basename(newpath))
		print(f"Mod '{self.slug}' has been {'enabled' if self.isDisabled() else 'disabled'}")
		os.rename(currentpath, newpath)

	@staticmethod
	def modInstalled(slug):
		return True if os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.ini")) or os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.toml")) else False

def addMod(ctx):
	slugs = [] + ctx.args["slugs"]
	if ctx.args["all"]:
		slugs.extend(listAll(ctx))
	if not slugs:
		raise NoTargetsError
	slugs = list(set(slugs))
	mods: List[ModType] = [ModType(slug) for slug in slugs if slug not in ctx.config["ignored-mods"]]

	i, toremove, checked = -1, [], []
	for mod in mods:
		checked.extend([mod.slug, mod.index["mod-id"]])
	progress = tqdm.tqdm(total=len(mods), desc=f"total {len(mods)}", unit="mods")
	while i < len(mods) - 1:
		progress.update(1)
		i += 1
		mod = mods[i]
		if not mod.api_data: # skip redundant get for dependencies
			mod.api_data = sources[mod.source].getAPI(ctx, mod.slug)
		if not isinstance(mod.api_data, dict):
			raise TargetNotFoundError(mod.slug)
		mod.source = mod.api_data["source"]
		logger.info("Successfully got api data for mod '%s'", mod.slug)
		mod.api_data["versions"] = sources[mod.source].parseAPI(ctx, mod.api_data)
		checked.extend([mod.slug, mod.api_data["id"]])
		if mod.isInstalled() and mod.isDisabled():
			progress.write(f"mod '{mod.slug}' is disabled, skipping")
			toremove.append(mod)
			continue
		if isinstance(mod.api_data["versions"], str):
			toremove.append(mod)
			continue
		if mod.source == "local":
			mod.slug = mod.api_data["versions"][0]["slug"]
			mod.index = indexing.get(ctx, mod.slug)
		elif mod.api_data["versions"][0]["id"] == mod.index["version-id"]:
			progress.write(f"Mod '{mod.slug}' already up to date, {'skipping' if ctx.args['operation'] == 'upgrade' or mod.slug not in ctx.args['slugs'] else 'reinstalling'}")
			if ctx.args["operation"] == "upgrade" or mod.slug not in ctx.args["slugs"]:
				toremove.append(mod)
				continue
		if ctx.args["explicit"]:
			continue
		for dependency in mod.api_data["versions"][0]["dependencies"]:
			if dependency["project_id"] in checked:
				continue
			dep_api_data = sources[mod.source].getAPI(ctx, dependency["project_id"])
			reason = 'optional' if dependency['dependency_type'] == 'optional' else 'dependency'
			progress.write(f"mod '{mod.slug}' is dependent on '{dep_api_data['slug']}' ({'required' if reason == 'dependency' else reason})\n" if not ModType.modInstalled(dep_api_data['slug']) else "", end="")
			checked.extend([dependency["project_id"], dep_api_data["slug"]])
			dep = ModType(dep_api_data["slug"], reason)
			dep.api_data = dep_api_data
			if dependency['dependency_type'] != 'optional' or ctx.config["get-optional-dependencies"] or ctx.args["optional"]:
				mods.append(dep)
			progress.total = len(mods)
			progress.refresh()
	progress.close()

	for mod in toremove:
		mods.remove(mod)
	if not mods:
		print("all mods are up to date")
		return

	_ = "" if ctx.args["noconfirm"] else confirm(ctx, mods)

	installMod(ctx, mods)

def removeMod(ctx, slugs=None):
	if slugs is None:
		slugs = [] + ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]

	if all(not mod.isInstalled() for mod in mods):
		print("no mods found")
		return
	for mod in mods:
		if not mod.isInstalled():
			raise TargetNotFoundError(mod.slug)

	_ = "" if ctx.args["noconfirm"] else confirm(ctx, mods)

def removeFinal(ctx, mods, suppressTranslation):
	for mod in mods:
		if not suppressTranslation and mod.slug in ("cardboard", "connector"):
			ctx.instance["translation-layer"] = "None"
			ctx.instance.write()
		if mod.index["index-version"] <= 4:
			if os.path.exists(os.path.join(mod.index["folder"], mod.index["filename"])):
				os.remove(os.path.join(mod.index["folder"], mod.index["filename"]))
			elif os.path.exists(os.path.join(mod.index["folder"], mod.index["filename"] + ".disabled")):
				os.remove(os.path.join(mod.index["folder"], mod.index["filename"] + ".disabled"))
		else:
			for file in [file for file in mod.getPath() if os.path.exists(file)]:
				os.remove(file)
		if mod.isInstalled():
			if os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{mod.slug}.mm.ini")):
				os.remove(os.path.join(ctx.instanceDir, ".content", f"{mod.slug}.mm.ini"))
			elif os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{mod.slug}.mm.toml")):
				os.remove(os.path.join(ctx.instanceDir, ".content", f"{mod.slug}.mm.toml"))

			if os.path.exists(os.path.join(mod.index["folder"], ".index", f"{mod.slug}.pw.toml")) and "index-compatibility" in ctx.instance:
				os.remove(os.path.join(mod.index["folder"], ".index", f"{mod.slug}.pw.toml"))
		logger.info("Removed content '%s'", mod.slug)
		print(f"Removed mod '{mod.slug}'\n" if ctx.args["operation"] == "remove" else "", end='')

def confirm(ctx, mods: List[ModType]):
	print("")
	op = "remove" if ctx.args["operation"] == "remove" else "download"
	totaloldsize = 0
	for mod in mods:
		if "size" in mod.index:
			totaloldsize += mod.index["size"]
		elif mod.index["index-version"] <= 4:
			if os.path.exists(mod.getPath()):
				os.path.getsize(mod.getPath())
		else:
			for file in mod.getPath():
				if os.path.exists(file):
					os.path.getsize(file)

	totalnewsize = sum(mod.api_data["versions"][0]["files"][0]["size"] for mod in mods) if op == "download"  else 0

	for mod in mods:
		print(f"Mod {mod.source}/{mod.slug} {mod.index['version']} --> {mod.api_data['versions'][0]['version_number'] if op == 'download'  else None}")
	print(f"\nTotal {op} size: {convertBytes(totalnewsize if op == 'download' else totaloldsize)}")
	print(f"Net upgrade Size: {convertBytes(totalnewsize - totaloldsize)}")
	yn = input(f"\n{ctx.color.INPUT}::{ctx.color.NORMAL} Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() not in ["y", "", "yes"]:
		logger.error("User declined %s", op)
		raise SystemExit

def queryMod(ctx):
	slugs = listAll(ctx) if not ctx.args["slugs"] else ctx.args["slugs"]
	mods = [ModType(slug) for slug in slugs]
	for mod in mods:
		if not mod.isInstalled():
			print(f"mod {mod.slug} is not installed")
			continue
		if ctx.args["explicit"] and mod.index["reason"] != "explicit":
			continue
		if ctx.args["dependency"] and mod.index["reason"] != "dependency":
			continue
		if ctx.args["optional"] and mod.index["reason"] != "optional":
			continue
		if not ctx.args["info"]:
			print(f"{mod.slug} {mod.index['version']}")
		else:
			print(f"Name{':'.rjust(13, ' ')} {mod.slug}")
			print(f"Version{':'.rjust(10, ' ')} {mod.index['version']}")
			print(f"Source{':'.rjust(11, ' ')} {mod.index['source']}")
			print(f"Description{':'.rjust(6, ' ')} {mod.index['description']}\n" if 'description' in mod.index else "", end="")
			print(f"Loader{':'.rjust(11, ' ')} {mod.index['loader']}\n" if 'loader' in mod.index else "", end="")
			print(f"Installed Size{':'.rjust(3, ' ')} {convertBytes(mod.index['filesize'])}\n" if 'filesize' in mod.index else "", end="")
			print(f"Install Date{':'.rjust(5, ' ')} {mod.index['date']}\n" if "date" in mod.index else "", end="")
			print(f"Install Reason{':'.rjust(3, ' ')} {mod.index['reason']}")
			print("")

def listAll(ctx) -> list:
	ls = []
	for file in os.listdir(os.path.join(ctx.instanceDir, ".content")):
		ls.append(file[:-8] if file.endswith(".mm.toml") else file[:-7])
	return ls

def toggleMod(ctx):
	slugs = ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]
	for mod in mods:
		mod.toggle()

def searchMod(ctx):
	query = ctx.args["query"]
	logger.info("Getting search data for query '%s'", query)
	queryData = {source: sources[source].searchAPI for source in sources if "SEARCH" in sources[source].TAGS}
	queryData = {"modrinth": modrinth.searchAPI(ctx, query), "hangar": hangar.searchAPI(ctx, query)}
	if not queryData["modrinth"]["hits"] and not queryData["hangar"]["hits"]:
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return
	queryData["all"] = queryData["modrinth"]["hits"]
	queryData["all"].extend(queryData["hangar"]["hits"])
	queryData["all"].sort(key=lambda x: x["downloads"])
	for hit in queryData["all"]:
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, ctx.instance["version"], ctx.instance["loader"])
		print(f"{hit['source']}/{hit['slug']} by {hit['author']} {'[Installed]' if ModType.modInstalled(hit['slug']) else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgradeMod(ctx):
	slugs = [] + ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	mods = [ModType(slug) for slug in slugs]
	for mod in mods:
		versions = []
		mod.api_data = {source: sources[source].getAPI(ctx, mod.slug) for source in sources if "EXTERNAL" in sources[source].TAGS}
		for source in [source for source in sources if "EXTERNAL" in sources[source].TAGS]:
			if not isinstance(mod.api_data[source], dict):
				continue
			mod.api_data[source]["versions"] = sources[source].parseAPI(ctx, mod.api_data[source])
			if isinstance(mod.api_data[source].get("versions"), str):
				continue
			if not versions:
				mod.api_data["type"] = mod.api_data[source]["project_type"]
			versions.extend(mod.api_data[source]["versions"])
		for version in versions:
			version["date"] = version.get("date_published", version.get("createdAt", 0))
		mod.api_data["versions"] = sorted(versions, key=lambda x: x['date'], reverse=True)

		for i, version in enumerate(reversed(mod.api_data["versions"])):
			suffix = "[INSTALLED]" if version['id'] == mod.index['version-id'] else '[CACHED]' if cache.isModCached(ctx, mod.slug, ctx.instance["loader"], version['version_number'], ctx.instance["version"]) else ''
			print(f"  {len(mod.api_data['versions']) - i - 1})\t{version['source']}/{mod.slug}\t{version['version_number']}\t{suffix}")

		choice = input(f"{ctx.color.INPUT}::{ctx.color.NORMAL} Choose version: ")
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
		mod.api_data[mod.source]["versions"][0] = mod.api_data["versions"][0]
		mod.api_data = mod.api_data[mod.source]

	_ = "" if ctx.args["noconfirm"] else confirm(ctx, mods)

	installMod(ctx, mods)

def installMod(ctx, mods):
	toignore = []
	progress = tqdm.tqdm(total=len(mods), desc=f"total {len(mods)}")
	for mod in mods:
		if ctx.args["ignore"] and not mod.isIgnored():
			ignore =  input(f"{ctx.color.INPUT}::{ctx.color.NORMAL} add {mod.slug} to ignored-mods? [y/N]: ").lower()
			if ignore == "y":
				toignore.append(mod.slug)
		removeFinal(mods, True)
		if mod.slug in ["connector", "cardboard"]:
			ctx.instance["translation-layer"] = "sinytra" if mod.slug == "connector" else "cardboard"
			ctx.instance.write()

		mod.api_data["versions"][0]["filepaths"] = sources[mod.api_data["versions"][0].get("source", "modrinth")].getMod(ctx, mod.slug, mod.api_data)
		indexing.mcmm(ctx, mod.slug, mod.api_data, mod.index["reason"], mod.api_data["versions"][0]["source"])
		cache.setModCache(ctx, mod.slug, ctx.instance["loader"], mod.api_data["versions"][0]['version_number'], ctx.instance["version"], mod.api_data["versions"][0]["folder"], mod.api_data["versions"][0]['files'][0]['filename'])
		progress.write(f"Mod '{mod.slug}' successfully updated")
		progress.update(1)
	progress.close()

	if ctx.args["ignore"]:
		slugs = ctx.args["slugs"] if slugs is None else slugs
		for slug in slugs:
			ctx.instance["ignored-mods"].append(slug)
		ctx.instance["ignored-mods"] = list(set(ctx.instance["ignored-mods"]))
		ctx.instance.write()

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

class sourceagnostic: # a fake source that looks up other sources
	TAGS = []
	@staticmethod
	def getAPI(ctx, slug):
		apiData = {source: sources[source].getAPI(ctx, slug) for source in sources if "EXTERNAL" in sources[source].TAGS}
		toremove = [source for source in apiData if not isinstance(apiData[source], dict)]
		for source in toremove:
			del apiData[source]
		if not apiData:
			raise TargetNotFoundError(slug)
		if len(list(apiData.keys())) >  1:
			print(f"found multiple sources for mod '{slug}'\n")
			for i, source in enumerate(reversed(apiData)):
				print(f"  {len(apiData) - i - 1})\t{source}/{slug}")
			choice = input(f"\n{ctx.color.INPUT}::{ctx.color.NORMAL} Choose source: ")
			try:
				choice = int(choice)
			except ValueError as exc:
				raise InvalidChoice(f"Invalid choice, could not cast '{choice}' to int") from exc
			if choice < 0 or choice >= len(apiData):
				raise InvalidChoice(f"Invalid choice, must be between 0 and {len(apiData) - 1}")
			return list(apiData.values())[choice]
		for s in apiData:
			if isinstance(apiData[s], dict):
				return apiData[s]
		return None

class SourceAbstract(Protocol):
	TAGS: list
	BANG: str
	@staticmethod
	def getMod(ctx: commons.Context, slug: str, modData: dict) -> list: ...
	@staticmethod
	def parseAPI(ctx: commons.Context, apiData: dict) -> list: ...
	@staticmethod
	def getAPI(ctx: commons.Context, slug: str) -> dict: ...
	@staticmethod
	def searchAPI(ctx: commons.Context, query: str) -> dict: ...

if ctx.args["operation"] in ["sync", "upgrade", "search", "downgrade"]: # only import sources when needed
	import modrinth, hangar, local, tqdm
	sources: dict[str, SourceAbstract] = {"local": local, "modrinth": modrinth, "hangar": hangar, "sourceagnostic": sourceagnostic}

if __name__ == "__main__":
	try:
		if ctx.lockneeded:
			if not os.path.exists(os.path.join(ctx.instanceDir, "mcmodman.lock")):
				fd = os.open(os.path.join(ctx.instanceDir, "mcmodman.lock"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
				with os.fdopen(fd, 'w', encoding='utf-8') as f:
					f.write("lock")
					logger.info("Setting lock")
			else:
				print("mcmodman is already running for this instance")
				logger.info("mcmodman.lock file already exists, exiting")
				raise LockExistsError("mcmodman is already running for this instance")

		operations = {"sync": addMod, "upgrade": addMod, "remove": removeMod, "clear-cache": cache.clearCache, "query": queryMod, "toggle": toggleMod, "search": searchMod, "downgrade": downgradeMod,
		"instance": instance.instanceMeta, "version": lambda _: print(commons.__version__)}
		operations[ctx.args["operation"]](ctx)
	except KeyboardInterrupt:
		print("Interrupt signal received")
		logger.info("Process interrupted by user")
	except LockExistsError as e:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} could not lock instance: File Exists\n\tIf you're sure mcmodman is not already running for this instance, you can remove {ctx.instanceDir}/mcmodman.lock")
		logger.critical("already running for instance")
		raise SystemExit from e
	except InvalidChoice as e:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} {e}")
	except NoValidVersions:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} could not find any valid versions")
	except NoTargetsError:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} no targets specified")
		logger.critical("user called operation that takes targets but no targets given")
	except TargetNotFoundError as e:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} target not found: {e}")
		logger.critical("user gave target that doesnt exist")
	except RuntimeError as e:
		print(f"{ctx.color.ERROR}An error occurred while running mcmodman{ctx.color.NORMAL}")
		logger.critical(e)
		raise
	except Exception as e: # allows for removing the lock file when an unhandled error occurs
		print(f"{ctx.color.ERROR}An unexpected error occured, {e}{ctx.color.NORMAL}")
		logger.critical(e)
		raise
	finally:
		if ctx.lockneeded and os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, "mcmodman.lock"))):
			logger.info("Removing lock")
			os.remove(os.path.expanduser(os.path.join(ctx.instanceDir, "mcmodman.lock")))
		logger.info("Exiting")
