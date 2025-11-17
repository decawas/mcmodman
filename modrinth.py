"""
modrinth api functions
"""
from hashlib import sha512
import logging, os
import pycurl, certifi, json
import cache

TAGS = ["SEARCH", "SYNC"]
BANG = "modrinth"
DB = "modrinth.db"

def getMod(ctx, slug: str, modData: dict) -> list:
	if cache.isModCached(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"]):
		cache.getModCache(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"], modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])
	else:
		with open(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']), "wb") as f:
			response = pycurl.Curl()
			response.setopt(response.URL, f"{modData['versions'][0]['files'][0]['url']}")
			response.setopt(response.CAINFO, certifi.where())
			response.setopt(response.WRITEDATA, f)
			response.setopt(response.USERAGENT, "mcmodman (https://github.com/decawas/mcmodman)")
			response.perform()
			response.close()

		if ctx.config["checksum"] in ["Always", "Download"]:
			perfcheck = True
		elif ctx.config["checksum"] == "Never":
			perfcheck = False
		else:
			perfcheck = True

		if perfcheck:
			print("Checking hash")
			with open(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']), 'rb') as f:
				checksum = sha512(f.read()).hexdigest()
			if modData["versions"][0]["files"][0]["hashes"]["sha512"] != checksum:
				print("Failed to validate file")
				os.remove(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData["versions"][0]['files'][0]['filename']))
				raise ChecksumError

		cache.setModCache(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"], modData["versions"][0]["folder"], modData['versions'][0]['files'][0]['filename'])
	return [os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])]

def parseAPI(ctx, apiData: dict) -> list:
	ptype, folder = projectGetType(ctx, apiData)
	if ptype == "modpack":
		print(f"{apiData['slug']} is a modpack")
		logger.error("mcmodman does not currently support modpacks, skipping")
		return "Modpack"

	mod_loader = ctx.instance["loader"] if ptype == "mod" else apiData["loaders"][0] if ptype in ["shader", "resourcepack"] else "datapack" if ptype == "datapack" else ""
	if ptype in ["shader", "resourcepack"] and ctx.instance["type"] != "client":
		print(f"{ptype}s do not work on servers, skipping")
		logger.warning("content of type '%s' can not be used on servers", ptype)
		return ptype
	if ptype == "datapack" and ctx.instance["type"] != "world":
		print("mcmodman only supports datapacks for worlds, skipping")
		logger.warning("content of type '%s' can only be used on worlds", ptype)
		return ptype

	matchesbychannel: dict = {"release": [], "beta": [], "alpha": [], "translation": []}
	for version in apiData["versions"]:
		version["source"] = "modrinth"
		version["date"] = version["date_published"]
		version["type"] = ptype
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
	return matches

def getAPI(ctx, slug: str) -> dict:
	cacheData = cache.getAPICache(ctx, "modrinth.db", slug)
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from modrinth", slug, slug)
		try:
			buffer = bytearray()
			response = pycurl.Curl()
			response.setopt(response.URL, f"https://api.modrinth.com/v2/project/{slug}")
			response.setopt(response.CAINFO, certifi.where())
			response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
			response.setopt(response.USERAGENT, "mcmodman (https://github.com/decawas/mcmodman)")
			response.perform()
			if buffer == b"":
				return 500
			modData = json.loads(buffer.decode("utf-8"))
			buffer = bytearray()
			response.setopt(response.URL, f"https://api.modrinth.com/v2/project/{slug}/version")
			response.perform()
			modData["versions"] = json.loads(buffer.decode("utf-8"))
			response.close()

			cache.setAPICache(ctx, "modrinth.db", modData['id'], modData)
			cache.setAPICache(ctx, "modrinth.db", modData['slug'], modData)
		except ZeroDivisionError:
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
		url = f'https://api.modrinth.com/v2/search?limit=48&index=downloads&query={query.replace(' ', '+')}'
		buffer = bytearray()
		response = pycurl.Curl()
		response.setopt(response.URL, url)
		response.setopt(response.CAINFO, certifi.where())
		response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
		response.setopt(response.USERAGENT, "mcmodman (https://github.com/decawas/mcmodman)")
		response.perform()
		queryData = json.loads(buffer.decode("utf-8"))
		response.close()

		cache.setAPICache(ctx, "modrinthsearch.db", queryData)

	for hit in queryData["hits"]:
		hit["source"] = "modrinth"

	return queryData

def projectGetType(ctx, apiData):
	if apiData["project_type"] == "modpack":
		ptype = "modpack"
		folder = ""
	elif apiData["project_type"] in ["shader", "resourcepack"]:
		ptype = apiData["project_type"]
		folder = os.path.join(ctx.instanceDir, "shaderpacks" if apiData["project_type"] == "shader" else "resourcepacks")
	elif apiData["project_type"] == "mod":
		ptype = "mod"
		folder = os.path.join(ctx.instanceDir, ctx.instance["modfolder"])
	else:
		raise ValueError

	return ptype, folder

logger = logging.getLogger(__name__)

class ChecksumError(Exception):
	"error: a mod failed the checksum"
