"""
modrinth api functions
"""
from hashlib import sha512
import logging, os
from requests import get, RequestException
import cache

TAGS = ["SEARCH", "EXTERNAL"]

def getMod(ctx, slug: str, modData: dict) -> None:
	if cache.isModCached(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"]):
		cache.getModCache(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"], modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])
		return

	url = f"{modData['versions'][0]['files'][0]['url']}"
	response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
	logger.info('Modrinth returned headers %s', response.headers)
	if response.status_code != 200:
		logger.error('Modrinth download returned %s', response.status_code)
		raise RuntimeError(f"Failed to download mod: HTTP {response.status_code}")

	with open(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']), "wb") as f:
		f.write(response.content)

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
	matches = matches = matchesbychannel.pop("release") + matchesbychannel.pop("beta") + matchesbychannel.pop("alpha") + matchesbychannel.pop("translation")
	if not matches:
		logger.error("No matching versions found for mod '%s", apiData['slug'])
		return "No version"
	return matches

def getAPI(ctx, slug: str) -> dict:
	cacheData = cache.getAPICache(ctx, slug, "modrinth")
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from modrinth", slug, slug)
		url = f"https://api.modrinth.com/v2/project/{slug}"
		try:
			response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
			if response.status_code != 200:
				return response.status_code
			modData = response.json()
			url = f"https://api.modrinth.com/v2/project/{slug}/version"
			response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
			response.raise_for_status()
			modData["versions"] = response.json()

			cache.setAPICache(ctx, slug, modData, "modrinth")
			if slug != modData['slug']:
				cache.setAPICache(ctx, modData['slug'], modData, "modrinth")
		except RequestException:
			modData = {"versions": []}

	modData["source"] = "modrinth"
	return modData

def searchAPI(ctx, query: str) -> dict:
	cacheData = cache.getAPICache(ctx, query, "modrinth")
	if cacheData:
		queryData = cacheData

	if "queryData" not in locals():
		logger.info("Could not find valid cache data for query '%s'", query)
		print(f"Querying modrinth with query '{query}'")
		url = f"https://api.modrinth.com/v2/search?limit=48&index=downloads&query={query.replace(' ', '+')}&facets=[[\"project_types!=modpack\"]]"
		try:
			response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
			response.raise_for_status()
			queryData = response.json()

			cache.setAPICache(ctx, query, queryData, "modrinth")
		except RequestException:
			queryData = {"hits": []}

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
