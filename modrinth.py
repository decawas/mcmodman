"""
modrinth api functions
"""
from hashlib import sha512
import logging, os
from requests import get, RequestException
import cache, commons

TAGS = ["SEARCH", "EXTERNAL"]

if not os.path.exists(os.path.join(commons.cacheDir, "modrinth-api")):
	os.makedirs(os.path.join(commons.cacheDir, "modrinth-api"))

def getMod(slug: str, mod_data: dict) -> None:
	if cache.isModCached(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version):
		print(f"Using cached version for mod '{slug}'")
		cache.getModCache(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename'])
		return

	print(f"Downloading mod '{slug}'")
	url = f"{mod_data['versions'][0]['files'][0]['url']}"
	response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
	logger.info('Modrinth returned headers %s', response.headers)
	if response.status_code != 200:
		logger.error('Modrinth download returned %s', response.status_code)
		raise RuntimeError(f"Failed to download mod: HTTP {response.status_code}")

	with open(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename']), "wb") as f:
		f.write(response.content)

	if commons.config["checksum"] in ["Always", "Download"]:
		perfcheck = True
	elif commons.config["checksum"] == "Never":
		perfcheck = False
	else:
		perfcheck = True

	if perfcheck:
		print("Checking hash")
		with open(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename']), 'rb') as f:
			checksum = sha512(f.read()).hexdigest()
		if mod_data["versions"][0]["files"][0]["hashes"]["sha512"] != checksum:
			print("Failed to validate file")
			os.remove(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data["versions"][0]['files'][0]['filename']))
			raise ChecksumError

	cache.setModCache(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version, mod_data["versions"][0]["folder"], mod_data['versions'][0]['files'][0]['filename'])

def parseAPI(api_data: dict) -> list:
	ptype, folder = projectGetType(api_data)
	if ptype == "modpack":
		print(f"{api_data['slug']} is a modpack")
		logger.error("mcmodman does not currently support modpacks, skipping")
		return "Modpack"

	mod_loader = commons.instancecfg["loader"] if ptype == "mod" else api_data["loaders"][0] if ptype in ["shader", "resourcepack"] else "datapack" if ptype == "datapack" else ""
	if ptype in ["shader", "resourcepack"] and commons.instancecfg["type"] != "client":
		print(f"{ptype}s do not work on servers, skipping")
		logger.warning("content of type '%s' can not be used on servers", ptype)
		return ptype
	if ptype == "datapack" and commons.instancecfg["type"] != "world":
		print("mcmodman only supports datapacks for worlds, skipping")
		logger.warning("content of type '%s' can only be used on worlds", ptype)
		return ptype

	matchesbychannel = {"release": [], "beta": [], "alpha": [], "translation": []}
	for version in api_data["versions"]:
		version["source"] = "modrinth"
		version["date"] = version["date_published"]
		version["type"] = ptype
		if commons.minecraft_version in version["game_versions"] and (mod_loader in version["loaders"] or (mod_loader in commons.loaderUpstreams and any(loader in commons.loaderUpstreams[mod_loader] for loader in version["loaders"]) and commons.config["allow-upstream"])):
			version["folder"] = folder
			matchesbychannel[version["version_type"]].append(version)
		elif commons.minecraft_version in version["game_versions"] and commons.instancecfg.get("translation-layer", None) == "cardboard" and (mod_loader in version["loaders"] or (mod_loader in commons.loaderUpstreams and any(loader in commons.loaderUpstreams["paper"] for loader in version["loaders"]) and commons.config["allow-upstream"])):
			version["folder"] = "plugins"
			matchesbychannel["translation"].append(version)
		elif commons.minecraft_version in version["game_versions"] and commons.instancecfg.get("translation-layer", None) == "sinytra" and (mod_loader in version["loaders"] or (mod_loader in commons.loaderUpstreams and any(loader in commons.loaderUpstreams["quilt"] for loader in version["loaders"]) and commons.config["allow-upstream"])):
			version["folder"] = "mods"
			matchesbychannel["translation"].append(version)
	matches = matches = matchesbychannel.pop("release") + matchesbychannel.pop("beta") + matchesbychannel.pop("alpha") + matchesbychannel.pop("translation")
	if not matches:
		logger.error("No matching versions found for mod '%s", api_data['slug'])
		return "No version"
	return matches

def getAPI(slug: str, depcheck: bool = False) -> dict:
	cacheData = cache.getAPICache(slug, "modrinth")
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from modrinth", slug, slug)
		print(f"Fetching api data for mod '{slug}'\n" if not depcheck else "", end='')
		url = f"https://api.modrinth.com/v2/project/{slug}"
		try:
			response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
			if response.status_code != 200:
				print(f"Mod '{slug}' not found")
				raise SystemExit
			modData = response.json()
			url = f"https://api.modrinth.com/v2/project/{slug}/version"
			response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
			response.raise_for_status()
			modData["versions"] = response.json()

			cache.setAPICache(slug, modData, "modrinth")
			if slug != modData['slug']:
				cache.setAPICache(modData['slug'], modData, "modrinth")
		except RequestException:
			modData = {"versions": []}

	modData["source"] = "modrinth"
	return modData

def searchAPI(query: str) -> dict:
	cacheData = cache.getAPICache(query, "modrinth")
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

			cache.setAPICache(query, queryData, "modrinth")
		except RequestException:
			queryData = {"hits": []}

	for hit in queryData["hits"]:
		hit["source"] = "modrinth"

	return queryData

def projectGetType(apiData):
	if apiData["project_type"] == "modpack":
		ptype = "modpack"
		folder = ""
	elif apiData["project_type"] in ["shader", "resourcepack"]:
		ptype = apiData["project_type"]
		folder = os.path.join(commons.instance_dir, "shaderpacks" if apiData["project_type"] == "shader" else "resourcepacks")
	elif apiData["project_type"] == "mod":
		ptype = "mod"
		folder = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"])
	else:
		raise ValueError

	return ptype, folder

logger = logging.getLogger(__name__)

class ChecksumError(Exception):
	"error: a mod failed the checksum"
