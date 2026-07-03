"""
main logic, and functions with front-end functionality
"""
import logger as logging
import os, commons, cache, indexing, instance
from typing import Protocol
sqlite3 = commons.sqlite3
ctx = commons.ctx

logger = logging.getLogger()

class ModType():
	def __init__(self, slug: str, reason: str="explicit"):
		self.source = None
		if "/" in slug:
			if any(slug.endswith(ext) for ext in (".jar", ".zip")):
				self.source = "local"
			elif slug.split("/")[0] not in [sources[source].BANG for source in sources if hasattr(sources[source], "BANG")]:
				raise SourceNotFoundError(slug.split("/")[0])
			for source in [source for source in sources if hasattr(sources[source], "BANG")]:
				if not slug.startswith(f"{sources[source].BANG}/"):
					continue
				slug = slug[len(f"{sources[source].BANG}/"):]
				self.source = source
				break
		self.slug = slug
		if "=" in self.slug:
			self.selectedversion = self.slug[self.slug.rfind("=") + 1:]
			self.slug = self.slug[:self.slug.rfind("=")]
		self.api_data = {}
		self.index: dict = indexing.get(ctx, self.slug, "explicit" if ctx.args["asexplicit"] else "dependency" if ctx.args["asdeps"] else reason)
		if self.index is None:
			raise TargetNotFoundError(slug)
		self.index["files"] = [file.replace("$INSTANCEDIR", ctx.instanceDir) for file in self.index["files"].split(" ") if file != ""]
		if self.index.get("source") is not None:
			self.source = self.index["source"]
		if self.source is None:
			self.source = "sourceagnostic"

	def isIgnored(self) -> bool:
		return self.slug in ctx.config["ignored-mods"]

	def isDisabled(self) -> bool | None: # returns true if disabled, false if enabled and none if not installed
		return None if not self.isInstalled() else False if not self.index["files"] or os.path.exists(self.index['files'][0]) else True if os.path.exists(f"{self.index['files'][0]}.disabled") else None

	def isInstalled(self) -> bool:
		return self.index["version"] != "None"

	def getPath(self) -> list:
		return self.index["files"]

	def toggle(self):
		if self.index["version"] == "None": # if not installed, raise target not found
			raise TargetNotFoundError(self.slug)
		if self.isDisabled():
			for file in self.index["files"]:
				currentpath, newpath = f"{file}.disabled", file
				os.rename(currentpath, newpath)
				logger.info("Moved content '%s' from %s to %s", self.slug, os.path.basename(currentpath), os.path.basename(newpath))
		else:
			for file in self.index["files"]:
				currentpath, newpath = file, f"{file}.disabled"
				os.rename(currentpath, newpath)
				logger.info("Moved content '%s' from %s to %s", self.slug, os.path.basename(currentpath), os.path.basename(newpath))
			print(f"Mod '{self.slug}' has been {'disabled' if self.isDisabled() else 'enabled'}")

def addMod(ctx):
	slugs = [] + ctx.args["slugs"]
	if ctx.args["all"]:
		slugs.extend(listAll(ctx))
	if not slugs:
		raise NoTargetsError
	slugs = list(set(slugs))
	global sources
	sources = {source: sources[source] for source in sources if "SYNC" in sources[source].TAGS}
	ctx.mods: list[ModType] = [ModType(slug) for slug in slugs if slug not in ctx.config["ignored-mods"]] 
	ctx.mods: list[ModType] = [mod for mod in ctx.mods if mod.source in sources]

	i, toremove, checked = -1, [], []
	for mod in ctx.mods:
		_ = checked.extend([mod.slug, mod.index["mod-id"]]) if "mod-id" in mod.index else checked.extend([mod.slug])
	progress = tqdm.tqdm(total=len(ctx.mods), desc=f"total {len(ctx.mods)}", unit="mods")
	while i < len(ctx.mods) - 1:
		progress.update(1)
		i += 1
		mod = ctx.mods[i]
		if not mod.api_data: # skip redundant get for dependencies
			mod.api_data = sources[mod.source].getAPI(ctx, mod.slug)
		if not isinstance(mod.api_data, dict):
			raise TargetNotFoundError(mod.slug)
		mod.source = mod.api_data["source"]
		logger.info("Successfully got api data for mod '%s'", mod.slug)
		mod.api_data["versions"] = sources[mod.source].parseAPI(ctx, mod.api_data)
		if hasattr(mod, "selectedversion"):
			for j, version in enumerate(mod.api_data["versions"]):
				if mod.selectedversion == version["id"] or mod.selectedversion == version["version_number"]:
					mod.api_data["selectedversion"] = j
					break
			if "selectedversion" not in mod.api_data:
				raise TargetNotFoundError(mod.selectedversion)
		else:
			mod.api_data["selectedversion"] = 0
		if mod.slug == "minecraft" and "minecraft" not in ctx.args["slugs"]:
			toremove.append(mod)
			continue
		checked.extend([mod.slug, mod.api_data["id"]])
		if mod.isInstalled() and mod.isDisabled():
			progress.write(f"mod '{mod.slug}' is disabled, skipping")
			toremove.append(mod)
			continue
		if isinstance(mod.api_data["versions"], str):
			toremove.append(mod)
			continue
		if mod.source == "local":
			mod.slug = mod.api_data["versions"][mod.api_data["selectedversion"]]["slug"]
			mod.index = indexing.get(ctx, mod.slug)
		elif mod.api_data["versions"][mod.api_data["selectedversion"]]["id"] == mod.index["version-id"]:
			progress.write(f"Mod '{mod.slug}' already up to date, {'skipping' if ctx.args['operation'] == 'upgrade' or mod.slug not in ctx.args['slugs'] else 'reinstalling'}")
			if ctx.args["operation"] == "upgrade" or mod.slug not in ctx.args["slugs"]:
				toremove.append(mod)
				continue
		if ctx.args["explicit"]:
			continue
		for dependency in mod.api_data["versions"][mod.api_data["selectedversion"]].get("dependencies", []):
			if dependency["project_id"] in checked:
				continue
			dep_api_data = sources[mod.source].getAPI(ctx, dependency["project_id"])
			reason = 'optional' if dependency['dependency_type'] == 'optional' else 'dependency'
			progress.write(f"mod '{mod.slug}' is dependent on '{dep_api_data['slug']}'", end="")
			progress.write(f" ({'required' if reason == 'dependency' else reason})", end="")
			progress.write(" [installed]\n" if ctx.instanceDB.execute("SELECT * FROM mods WHERE slug=?", (dep_api_data["slug"],)).fetchone() is not None else "\n", end="")
			checked.extend([dependency["project_id"], dep_api_data["slug"]])
			dep = ModType(dep_api_data["slug"], reason)
			dep.api_data = dep_api_data
			if dependency['dependency_type'] != 'optional' or ctx.config["get-optional-dependencies"] or ctx.args["optional"]:
				ctx.mods.append(dep)
			progress.total = len(ctx.mods)
			progress.refresh()
	progress.close()

	for mod in toremove:
		ctx.mods.remove(mod)

	if not ctx.mods:
		print("all mods are up to date")
		return
	
	_ = "" if ctx.args["noconfirm"] else confirm(ctx)

	installMod(ctx)

def removeMod(ctx, slugs=None):
	if slugs is None:
		slugs = [] + ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	ctx.mods = [ModType(slug) for slug in slugs]

	if all(not mod.isInstalled() for mod in ctx.mods):
		print("no mods found")
		return
	for mod in ctx.mods:
		if not mod.isInstalled():
			raise TargetNotFoundError(mod.slug)

	_ = "" if ctx.args["noconfirm"] else confirm(ctx)

	removeFinal(ctx, ctx.mods)

def removeFinal(ctx, mods):
	for mod in mods:
		if not mod.isInstalled():
			continue

		for file in [file for file in mod.getPath() if os.path.exists(file)] if not mod.isDisabled() else [f"{file}.disabled" for file in mod.getPath() if os.path.exists(f"{file}.disabled")]:
			os.remove(file)
		ctx.instanceDB.execute("DELETE FROM mods WHERE slug=?", (mod.slug,))
		ctx.instanceDB.commit()
		if os.path.exists(os.path.join(ctx.instanceDir, "mods", ".index", f"{mod.slug}.pw.toml")) and "index-compatibility" in ctx.instance:
			os.remove(os.path.join( ctx.instanceDir,"mods", ".index", f"{mod.slug}.pw.toml"))
		logger.info("Removed content '%s'", mod.slug)
		print(f"Removed mod '{mod.slug}'\n" if ctx.args["operation"] == "remove" else "", end='')

def confirm(ctx):
	print("")
	op = "remove" if ctx.args["operation"] == "remove" else "download"
	totaloldsize = 0
	for mod in ctx.mods:
		if "filesize" in mod.index:
			totaloldsize += mod.index["filesize"]
		for file in mod.getPath():
			if os.path.exists(file):
				totaloldsize += os.path.getsize(file)
	totalnewsize = sum(mod.api_data["versions"][mod.api_data["selectedversion"]]["files"][0]["size"] for mod in ctx.mods if "files" in mod.api_data["versions"][mod.api_data["selectedversion"]]) if op == "download" else sum(mod.index.get("filesize", 0) for mod in ctx.mods)

	for mod in ctx.mods:
		print(f"Mod {mod.source}/{mod.slug} {mod.index['version']} --> {mod.api_data['versions'][mod.api_data['selectedversion']]['version_number'] if op == 'download'  else None}")
	print(f"\nTotal {op} size: {convertBytes(totalnewsize if op == 'download' else totaloldsize)}")
	print(f"Net upgrade Size: {convertBytes(totalnewsize - totaloldsize)}")
	yn = input(f"\n{ctx.color.INPUT}::{ctx.color.NORMAL} Proceed with download? [Y/n]: ")
	print("")
	if yn.lower() not in ["y", "", "yes"]:
		logger.error("User declined %s", op)
		raise SystemExit

def queryMod(ctx):
	slugs = listAll(ctx) if not ctx.args["slugs"] else ctx.args["slugs"]
	ctx.mods = [ModType(slug) for slug in slugs]
	for mod in ctx.mods:
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
			print(f"Name            : {mod.slug}")
			print(f"Version         : {mod.index['version']}")
			print(f"Source          : {mod.index['source']}")
			print(f"Description     : {mod.index['description']}\n" if 'description' in mod.index else "", end="")
			if mod.index['loader'] != "": print(f"Loader          : {mod.index['loader']}\n" if 'loader' in mod.index else "", end="")
			if mod.index['filesize'] != 0: print(f"Installed Size  : {convertBytes(mod.index['filesize'])}\n" if 'filesize' in mod.index else "", end="")
			print(f"Install Date    : {mod.index['date']}\n" if "date" in mod.index else "", end="")
			print(f"Install Reason  : {mod.index['reason']}")
			print("")

def listAll(ctx) -> list:
	ls = [a[0] for a in ctx.instanceDB.execute("SELECT slug FROM mods").fetchall()]
	return ls

def toggleMod(ctx):
	slugs = ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	ctx.mods = [ModType(slug) for slug in slugs]
	for mod in ctx.mods:
		mod.toggle()

def searchMod(ctx):
	query = ctx.args["query"]
	logger.info("Getting search data for query '%s'", query)
	queryData = {source: sources[source].searchAPI(ctx, query) for source in sources if "SEARCH" in sources[source].TAGS}
	if not any(bool(queryData[source]["hits"]) for source in queryData):
		print(f"No results found for query '{query}'")
		logger.info("No results found for query '%s'", query)
		return
	queryData["all"] = queryData["modrinth"]["hits"]
	queryData["all"].extend(queryData["hangar"]["hits"])
	queryData["all"].sort(key=lambda x: x["downloads"])
	for hit in queryData["all"]:
		logger.info("Got hit '%s' for query '%s' with facets: [[\"project_types!=modpack\"],[\"versions:%s\"],[\"categories:%s\"]]", hit['slug'], query, ctx.instance["version"], ctx.instance["loader"])
		print(f"{hit['source']}/{hit['slug']} by {hit['author']} {'[Installed]' if ctx.instanceDB.execute('SELECT * FROM mods WHERE slug=?', (hit['slug'],)).fetchone() else ''}")
		print(f"\t{hit['description'].splitlines()[0]}")

def downgradeMod(ctx):
	slugs = [] + ctx.args["slugs"]
	if not slugs:
		raise NoTargetsError
	ctx.mods = [ModType(slug) for slug in slugs]
	for mod in ctx.mods:
		mod.api_data["selectedversion"] = 0
		versions = []
		mod.api_data = {source: sources[source].getAPI(ctx, mod.slug) for source in sources if "DOWNGRADE" in sources[source].TAGS}
		mod.api_data = {source: mod.api_data[source] for source in mod.api_data if mod.api_data[source] != 500}
		if not mod.api_data:
			raise TargetNotFoundError(mod.slug)
		for source in [source for source in mod.api_data]:
			if not isinstance(mod.api_data[source], dict):
				continue
			mod.api_data[source]["versions"] = sources[source].parseAPI(ctx, mod.api_data[source])
			if isinstance(mod.api_data[source].get("versions"), str):
				continue
			if not versions:
				mod.api_data["type"] = mod.api_data[source]["project_types"][0]
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

		mod.source = mod.api_data['versions'][choice]["source"]
		mod.api_data[mod.source]["versions"][choice] = mod.api_data["versions"][choice]
		mod.api_data = mod.api_data[mod.source]
		mod.api_data["selectedversion"] = choice

	_ = "" if ctx.args["noconfirm"] else confirm(ctx)

	installMod(ctx)

def installMod(ctx):
	toignore = []
	progress = tqdm.tqdm(total=len(ctx.mods), desc=f"total {len(ctx.mods)}")
	for mod in ctx.mods:
		if ctx.args["ignore"] and not mod.isIgnored():
			ignore =  input(f"{ctx.color.INPUT}::{ctx.color.NORMAL} add {mod.slug} to ignored-mods? [y/N]: ").lower()
			if ignore == "y":
				toignore.append(mod.slug)
		removeFinal(ctx, [mod])
		if not os.path.exists(os.path.join(ctx.instanceDir, mod.api_data["versions"][mod.api_data["selectedversion"]].get("folder", "mods"))):
			os.makedirs(os.path.join(ctx.instanceDir, mod.api_data["versions"][mod.api_data["selectedversion"]].get("folder", "mods")))
		mod.api_data["versions"][mod.api_data["selectedversion"]]["filepaths"] = sources[mod.api_data["versions"][mod.api_data["selectedversion"]].get("source", "modrinth")].getMod(ctx, mod.slug, mod.api_data, progress)
		_ = cache.setModCache(ctx, mod.slug, ctx.instance["loader"], mod.api_data["versions"][mod.api_data["selectedversion"]]['version_number'], ctx.instance["version"], mod.api_data["versions"][mod.api_data["selectedversion"]]["folder"], mod.api_data["versions"][mod.api_data["selectedversion"]]['files'][0]['filename']) if "folder" in mod.api_data["versions"][mod.api_data["selectedversion"]] else ""
		indexing.mcmm(ctx, mod.slug, mod.api_data, mod.index["reason"], mod.api_data["versions"][mod.api_data["selectedversion"]]["source"])
		progress.write(f"Mod '{mod.slug}' successfully updated")
		progress.update(1)
	progress.close()

	if ctx.args["ignore"]:
		ctx.instance["ignored-mods"].extend(toignore)
		ctx.instanceDB.execute(
			"UPDATE metadata SET ignoredhyphenmods=?",
			(" ".join(ctx.instance["ignored-mods"])))
		ctx.instanceDB.commit()

def convertBytes(size):
	for unit in ['B', 'KB', 'MB', 'GB']:
		if -1024 < size < 1024:
			break
		size /= 1024.0
	return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} {unit}"

class LockExistsError(Exception):
	"error: could not lock instance: File Exists"
class NoValidVersions(Exception):
	"error: could not find any valid versions"
class NoTargetsError(Exception):
	"error: no targets specified"
class SourceNotFoundError(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)
class TargetNotFoundError(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)
class InvalidChoice(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)

class sourceagnostic: # a fake source that looks up other sources
	TAGS = ["SYNC"]
	@staticmethod
	def getAPI(ctx, slug):
		apiData = {source: sources[source].getAPI(ctx, slug) for source in sources if "SYNC" in sources[source].TAGS and source != "sourceagnostic"}
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

sources = {}
if ctx.args["operation"] in ["sync", "upgrade", "search", "downgrade", "clear-cache"]: # only import sources when needed
	import modrinth, hangar, local, tqdm
	sources: dict[str, SourceAbstract] = {"local": local, "modrinth": modrinth, "hangar": hangar, "sourceagnostic": sourceagnostic}

def cc_wrap(ctx):
	cache.clearCache(ctx, sources)

if __name__ == "__main__":
	try:
		if ctx.args["operation"] not in ["clear-cache", "instance"] or (ctx.args["operation"] == "instance" and ctx.args["suboperation"] == "export"):
			if not os.path.exists(os.path.join(ctx.instanceDir, ".mcmodman.db")):
				instance.instanceFirstrun(ctx)
			try:
				ctx.instanceDB = sqlite3.connect(os.path.join(ctx.instanceDir, ".mcmodman.db"))
			except sqlite3.OperationalError:
				raise LockExistsError
			
			ctx.instance = ctx.instanceDB.execute("""SELECT * FROM metadata""").fetchone()
			ctx.instance = {k: v for k, v in zip([v[0].replace("hyphen", "-") for v in list(ctx.instanceDB.execute("SELECT name FROM pragma_table_info('metadata');"))], ctx.instance)}
			ctx.instance["ignored-mods"] = ctx.instance["ignored-mods"].split(" ")

		operations = {"sync": addMod, "upgrade": addMod, "remove": removeMod, "clear-cache": cc_wrap, "query": queryMod, "toggle": toggleMod, "search": searchMod, "downgrade": downgradeMod,
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
	except SourceNotFoundError as e:
		print(f"{ctx.color.ERROR}error:{ctx.color.NORMAL} source not found: {e}")
		logger.critical("user gave source that doesnt exist")
	except Exception as e: # allows for removing the lock file when an unhandled error occurs
		print(f"{ctx.color.ERROR}An unexpected error occurred, {e}{ctx.color.NORMAL}")
		logger.critical(e)
		raise
	finally:
		if hasattr(ctx, "instanceDB"):
			logger.info("Removing lock")
			ctx.instanceDB.close()
		logger.info("Exiting")
