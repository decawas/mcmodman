"""
hangar api functions
"""
from hashlib import sha256
import logging, os
from requests import get
import cache, commons

if not os.path.exists(os.path.join(commons.cacheDir, "hangar-api")):
	os.makedirs(os.path.join(commons.cacheDir, "hangar-api"))

def getMod(slug: str, mod_data: dict) -> None:
	if cache.isModCached(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version):
		print(f"Using cached version for plugin '{slug}'")
		cache.getModCache(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename'])
		return

	print(f"Downloading plugin '{slug}'")
	url = mod_data['versions'][0]['files'][0]['url']
	response = get(url, timeout=30)
	logger.info('Hangar returned headers %s', response.headers)
	if response.status_code != 200:
		logger.error('Hangar download returned %s', response.status_code)
		raise RuntimeError(f"Failed to download plugin: HTTP {response.status_code}")

	with open(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename']), "wb") as f:
		f.write(response.content)

	if commons.config["checksum"] in ["Always", "Download"]:
		perfcheck = True
	elif commons.config["checksum"] == "Never":
		perfcheck = False
	else:
		perfcheck = True

	if perfcheck and mod_data['versions'][0]['files'][0].get("hashes"):
		print("Checking hash")
		with open(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename']), 'rb') as f:
			checksum = sha256(f.read()).hexdigest()
		if mod_data['versions'][0]['files'][0]['hashes']['sha256'] != checksum:
			print("Failed to validate file")
			os.remove(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename']))
			raise ChecksumError
	elif perfcheck:
		print(f"warning: could not verify mod {slug}, no checksum provided")

	cache.setModCache(slug, commons.mod_loader, mod_data['versions'][0]['version_number'], commons.minecraft_version, mod_data['versions'][0]["folder"], mod_data['versions'][0]['files'][0]['filename'])

def parseAPI(apiData: dict) -> list:
	matches = {"release": [], "snapshot": [], "alpha": [], "translation": []}
	for version in apiData["versions"]["result"]:
		if commons.minecraft_version in version["platformDependencies"]["PAPER"]:
			version["folder"] = "plugins"
			version["source"] = "hangar"
			versionf = {"id": str(version["id"]), "version_number": version["name"], "name": version["name"], "dependencies": [], "files": [{"filename": version["downloads"]["PAPER"].get("fileInfo", {}).get("name") or f"{apiData['namespace']['slug']}-{version['name']}.jar", "size": version["downloads"]["PAPER"].get("fileInfo", {}).get("sizeBytes", 0), "url": version["downloads"]["PAPER"].get("downloadUrl") or version["downloads"]["PAPER"].get("externalUrl"), "hashes": {"sha256": version["downloads"]["PAPER"].get("fileInfo", {}).get("sha256Hash", "")}}], "folder": "plugins", "source": "hangar"}
			versionf["date"] = version["createdAt"]
			if commons.instancecfg["loader"] == "paper" or (commons.instancecfg["loader"] in ["folia", "purpur"] and commons.config["allow-upstream"]) or (commons.instancecfg["loader"] == "folia" and "SUPPORTS_FOLIA" in version["settings"]["tags"]):
				matches[version["channel"]["name"].lower()].append(versionf)
			elif commons.instancecfg.get("translation-layer", None) == "cardboard":
				matches["translation"].append(versionf)

	matches = matches["release"] + matches["snapshot"] + matches["alpha"] + matches["translation"]
	if not matches:
		logger.error("No matching versions found for mod '%s'", apiData['namespace']['slug'])
		return "No version"
	return matches

def getAPI(slug: str, depcheck: bool = False) -> dict:
	cacheData = cache.getAPICache(slug, "hangar")
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from hangar", slug, slug)
		print(f"Fetching api data for mod '{slug}'\n" if not depcheck else "", end='')

		url = f"https://hangar.papermc.io/api/v1/projects/{slug}"
		response = get(url, timeout=30)
		if response.status_code != 200:
			return "mod not found"
		modData = response.json()
		url = f"https://hangar.papermc.io/api/v1/projects/{slug}/versions?limit=25"
		response = get(url, timeout=30)
		response.raise_for_status()
		modData["versions"] = response.json()

		cache.setAPICache(slug, modData, "hangar")

	modData["source"] = "hangar"
	modData["type"] = "plugin"
	return modData

def searchAPI(query: str) -> dict:
	cacheData = cache.getAPICache(query, "hangar")
	if cacheData:
		queryData = cacheData

	if "queryData" not in locals():
		logger.info("Could not find valid cache data for query '%s'", query)
		print(f"Querying hangar with query '{query}'")
		url = f"https://hangar.papermc.io/api/v1/projects?sort=downloads&platform=paper&q={query.replace(' ', '+')}&version={commons.minecraft_version}"
		response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		response.raise_for_status()
		queryData = response.json()

		cache.setAPICache(query, queryData, "hangar")

	queryData["hits"] = queryData.pop("result")
	for hit in queryData["hits"]:
		hit["slug"] = hit["namespace"]["slug"]
		hit["author"] = hit["namespace"]["owner"]
		hit["downloads"] = hit["stats"]["downloads"]
		hit["source"] = "hangar"

	return queryData

def projectGetType(apiData):
	return "plugin", "plugins"

class ChecksumError(Exception):
	"error: a mod failed the checksum"

logger = logging.getLogger(__name__)
