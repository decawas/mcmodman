"""
modrinth api functions
"""
from hashlib import sha512
import logger as logging
import os
import pycurl, certifi, json
import cache

TAGS = ["SEARCH", "SYNC", "DOWNGRADE"]
BANG = "modrinth"
DB = "modrinth.db"

def getMod(ctx, slug: str, modData: dict, progress=None) -> list:
	if cache.isModCached(ctx, slug, ctx.instance["loader"], modData['versions'][modData["selectedversion"]]['version_number'], ctx.instance["version"]):
		cache.getModCache(ctx, slug, ctx.instance["loader"], modData['versions'][modData["selectedversion"]]['version_number'], ctx.instance["version"], modData['versions'][modData["selectedversion"]]["folder"], modData['versions'][modData["selectedversion"]]['files'][0]['filename'])
	else:
		with open(os.path.join(ctx.instanceDir, modData['versions'][modData["selectedversion"]]["folder"], modData['versions'][modData["selectedversion"]]['files'][0]['filename']), "wb") as f:
			response = pycurl.Curl()
			response.setopt(response.URL, f"{modData['versions'][modData["selectedversion"]]['files'][0]['url']}")
			response.setopt(response.CAINFO, certifi.where())
			response.setopt(response.WRITEDATA, f)
			response.setopt(response.USERAGENT, "mcmodman (https://codeberg.org/ekno/mcmodman)")
			response.perform()
			response.close()

		if ctx.config["checksum"] in ["Always", "Download"]:
			perfcheck = True
		elif ctx.config["checksum"] == "Never":
			perfcheck = False
		else:
			perfcheck = True

		if perfcheck:
			if progress is not None:
				progress.write("Checking hash")
			with open(os.path.join(ctx.instanceDir, modData['versions'][modData["selectedversion"]]["folder"], modData['versions'][modData["selectedversion"]]['files'][0]['filename']), 'rb') as f:
				checksum = sha512(f.read()).hexdigest()
			if modData["versions"][modData["selectedversion"]]["files"][0]["hashes"]["sha512"] != checksum:
				print("Failed to validate file")
				os.remove(os.path.join(ctx.instanceDir, modData['versions'][modData["selectedversion"]]["folder"], modData["versions"][modData["selectedversion"]]['files'][0]['filename']))
				raise ChecksumError

		cache.setModCache(ctx, slug, ctx.instance["loader"], modData['versions'][modData["selectedversion"]]['version_number'], ctx.instance["version"], modData["versions"][modData["selectedversion"]]["folder"], modData['versions'][modData["selectedversion"]]['files'][0]['filename'])
	return [os.path.join(ctx.instanceDir, modData['versions'][modData["selectedversion"]]["folder"], modData['versions'][modData["selectedversion"]]['files'][0]['filename'])]

def parseAPI(ctx, apiData: dict) -> list:
	if "modpack" in apiData["project_types"] or "minecraft_java_server" in apiData["project_types"]:
		print(f"{apiData['slug']} is a modpack")
		logger.error("mcmodman does not currently support modpacks, skipping")
		return "Modpack"

	if "mod" in apiData["project_types"]:
		if ctx.instance["type"] == "world" and "datapack" not in apiData["project_types"]:
			print("mods are not supported for worlds, skipping")
			logger.warning("content of type 'mod' can not be used on worlds")
			return "mod"
		mod_loader = ctx.instance["loader"]
		folder = os.path.join(ctx.instanceDir, "mods")
	if "plugins" in apiData["project_types"]:
		if ctx.instance["type"] == "world" and "datapack" not in apiData["project_types"]:
			print("worlds do not support plugins for worlds, skipping")
			logger.warning("content of type 'plugins' can not be used on worlds")
			return "plugin"
		mod_loader = ctx.instance["loader"]
		folder = os.path.join(ctx.instanceDir, "plugins")
	if "shader" in apiData["project_types"] or "resourcepack" in apiData["project_types"]:
		if ctx.instance["type"] != "client":
			print(f"{"shaderpacks" if "shader" in apiData["project_types"] else "resourcepacks"} do not work on servers or worlds, skipping")
			logger.warning("content of type '%s' can not be used on servers or worlds", apiData["project_types"][0])
			return apiData["project_types"][0]
		mod_loader = apiData["loaders"][0]
		folder = os.path.join(ctx.instanceDir, "shaderpacks" if "shader" in apiData["project_types"] else "resourcepacks")
	if "datapack" in apiData["project_types"] and "mod_loader" not in locals():
		if ctx.instance["type"] != "world":
			print("datapacks are only for worlds, skipping")
			logger.warning("content of type 'datapack' can only be used on worlds")
			return "datapack"
		mod_loader = "datapack"
		folder = os.path.join(ctx.instanceDir, "datapacks")
	if "mod_loader" not in locals():
		return "unknown type"

	matchesbychannel: dict = {"release": [], "beta": [], "alpha": [], "translation": []}
	for version in apiData["versions"]:
		version["source"] = "modrinth"
		version["date"] = version["date_published"]
		version["type"] = os.path.basename(folder)[:-1]
		if ctx.instance["version"] in version["game_versions"] and (mod_loader in version["loaders"] or (mod_loader in ctx.loaderUpstreams and any(loader in ctx.loaderUpstreams[mod_loader] for loader in version["loaders"]) and ctx.config["allow-upstream"])):
			version["folder"] = os.path.basename(folder)
			matchesbychannel[version["version_type"]].append(version)
		elif ctx.instance["version"] in version["game_versions"] and ctx.instance.get("translation-layer", None) == "cardboard" and (mod_loader in version["loaders"] or (mod_loader in ctx.loaderUpstreams and any(loader in ctx.loaderUpstreams["paper"] for loader in version["loaders"]) and ctx.config["allow-upstream"])):
			version["folder"] = "plugins"
			matchesbychannel["translation"].append(version)
		elif ctx.instance["version"] in version["game_versions"] and ctx.instance.get("translation-layer", None) == "sinytra" and (mod_loader in version["loaders"] or (mod_loader in ctx.loaderUpstreams and any(loader in ctx.loaderUpstreams["quilt"] for loader in version["loaders"]) and ctx.config["allow-upstream"])):
			version["folder"] = "mods"
			matchesbychannel["translation"].append(version)
	matches = matchesbychannel.pop("release") + matchesbychannel.pop("beta") + matchesbychannel.pop("alpha") + matchesbychannel.pop("translation")
	if not matches:
		logger.error("No matching versions found for mod '%s'", apiData['slug'])
		return "No version"
	apiData["description"] = apiData["summary"]
	return matches

def getAPI(ctx, slug: str) -> dict:
	cacheData = cache.getAPICache(ctx, "modrinth.db", slug)
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data from modrinth", slug)
		try:
			buffer = bytearray()
			response = pycurl.Curl()
			response.setopt(response.URL, f"https://api.modrinth.com/v3/project/{slug}")
			response.setopt(response.CAINFO, certifi.where())
			response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
			response.setopt(response.USERAGENT, "mcmodman (https://github.com/decawas/mcmodman)")
			response.perform()
			if buffer == b"":
				return 500
			modData = json.loads(buffer.decode("utf-8"))
			buffer = bytearray()
			response.setopt(response.URL, f"https://api.modrinth.com/v3/project/{slug}/version")
			response.perform()
			modData["versions"] = json.loads(buffer.decode("utf-8"))
			response.close()

			cache.setAPICache(ctx, "modrinth.db", modData['id'], modData)
			cache.setAPICache(ctx, "modrinth.db", modData['slug'], modData)
		except pycurl.error:
			modData = {"versions": []}
	
	modData["source"] = "modrinth"
	return modData

def searchAPI(ctx, query: str) -> dict:
	cacheData = cache.getAPICache(ctx, "modrinthsearch.db", query, )
	if cacheData:
		queryData = cacheData

	if "queryData" not in locals():
		logger.info("Could not find valid cache data for query '%s'", query)
		print(f"Querying modrinth with query '{query}'")
		url = f'https://api.modrinth.com/v3/search?limit=48&index=downloads&query={query.replace(' ', '+')}'
		buffer = bytearray()
		response = pycurl.Curl()
		response.setopt(response.URL, url)
		response.setopt(response.CAINFO, certifi.where())
		response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
		response.setopt(response.USERAGENT, "mcmodman (https://codeberg.org/ekno/mcmodman)")
		response.perform()
		queryData = json.loads(buffer.decode("utf-8"))
		response.close()

		cache.setAPICache(ctx, "modrinthsearch.db", query, queryData)

	for hit in queryData["hits"]:
		hit["source"] = "modrinth"
		hit["description"] = hit["summary"]
	return queryData

logger = logging.getLogger()

class ChecksumError(Exception):
	"error: a mod failed the checksum"
