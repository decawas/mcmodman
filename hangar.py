"""
hangar api functions
"""
from hashlib import sha256
import logging, os
import pycurl, certifi, json
import cache

TAGS = ["SEARCH", "EXTERNAL"]
BANG = "hangar"
DB = "hangar.db"

def getMod(ctx, slug: str, modData: dict) -> list:
	if cache.isModCached(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"]):
		print(f"Using cached version for plugin '{slug}'")
		cache.getModCache(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"], modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])
		
	else:
		with open(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']), "wb") as f:
			response = pycurl.Curl()
			response.setopt(response.URL, f"{modData['versions'][0]['files'][0]['url']}")
			response.setopt(response.CAINFO, certifi.where())
			response.setopt(response.WRITEDATA, f)
			response.perform()
			response.close()

		if ctx.config["checksum"] in ["Always", "Download"]:
			perfcheck = True
		elif ctx.config["checksum"] == "Never":
			perfcheck = False
		else:
			perfcheck = True

		if perfcheck and modData['versions'][0]['files'][0].get("hashes"):
			if not modData['versions'][0]['files'][0].get("hashes"):
				print(f"warning: could not verify mod {slug}, no checksum provided")
			else:
				print("Checking hash")
				with open(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']), 'rb') as f:
					checksum = sha256(f.read()).hexdigest()
				if modData['versions'][0]['files'][0]['hashes']['sha256'] != checksum:
					print("Failed to validate file")
					os.remove(os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename']))
					raise ChecksumError

		cache.setModCache(ctx, slug, ctx.instance["loader"], modData['versions'][0]['version_number'], ctx.instance["version"], modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])
	return [os.path.join(ctx.instanceDir, modData['versions'][0]["folder"], modData['versions'][0]['files'][0]['filename'])]

def parseAPI(ctx, apiData: dict) -> list:
	matchesbychannel = {"release": [], "snapshot": [], "alpha": [], "translation": []}
	for version in apiData["versions"]:
		if ctx.instance["version"] not in version["platformDependencies"]["PAPER"]:
			continue
		version["folder"] = "plugins"
		version["source"] = "hangar"
		versionf = {"id": str(version["id"]), "version_number": version["name"], "name": version["name"], "dependencies": [], "files": [{"filename": version["downloads"]["PAPER"].get("fileInfo", {}).get("name") or f"{apiData['namespace']['slug']}-{version['name']}.jar", "size": version["downloads"]["PAPER"].get("fileInfo", {}).get("sizeBytes", 0), "url": version["downloads"]["PAPER"].get("downloadUrl") or version["downloads"]["PAPER"].get("externalUrl"), "hashes": {"sha256": version["downloads"]["PAPER"].get("fileInfo", {}).get("sha256Hash", "")}}], "folder": "plugins", "source": "hangar"}
		versionf["date"] = version["createdAt"]
		if ctx.instance["loader"] == "paper" or (ctx.instance["loader"] in ["folia", "purpur"] and ctx.config["allow-upstream"]) or (ctx.instance["loader"] == "folia" and "SUPPORTS_FOLIA" in version["settings"]["tags"]):
			matchesbychannel[version["channel"]["name"].lower()].append(versionf)
		elif ctx.instance.get("translation-layer", None) == "cardboard":
			matchesbychannel["translation"].append(versionf)

	matches = matchesbychannel.pop("release") + matchesbychannel.pop("snapshot") + matchesbychannel.pop("alpha") + matchesbychannel.pop("translation")
	if not matches:
		logger.error("No matching versions found for mod '%s", apiData['namespace']['slug'])
		return "No version"
	return matches

def getAPI(ctx, slug: str) -> dict:
	if ctx.instance["loader"] not in ["paper", "folia"]:
		return 500
	cacheData = cache.getAPICache(ctx,  "hangar.db", slug)
	if cacheData:
		modData = cacheData

	if "modData" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from hangar", slug, slug)

		buffer = bytearray()
		response = pycurl.Curl()
		response.setopt(response.URL, f"https://hangar.papermc.io/api/v1/projects/{slug}")
		response.setopt(response.CAINFO, certifi.where())
		response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
		response.perform()
		modData = json.loads(buffer.decode("utf-8"))
		if modData.get("httpError") != None:
			return 404
		buffer = bytearray()
		response.setopt(response.URL, f"https://hangar.papermc.io/api/v1/projects/{slug}/versions?limit=25")
		response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
		response.perform()
		modData["versions"] = json.loads(buffer.decode("utf-8"))
		response.close()
		cache.setAPICache(ctx, "hangar.db", modData["slug"], modData)
		cache.setAPICache(ctx, "hangar.db", modData["id"], modData)

	modData["source"] = "hangar"
	modData["type"] = "plugin"
	return modData

def searchAPI(ctx, query: str) -> dict:
	cacheData = cache.getAPICache(ctx, "hangarsearch.db", query)
	if cacheData:
		queryData = cacheData

	if "queryData" not in locals():
		logger.info("Could not find valid cache data for query '%s'", query)
		print(f"Querying hangar with query '{query}'")
		url = f"https://hangar.papermc.io/api/v1/projects?sort=downloads&platform=paper&q={query.replace(' ', '+')}&version={ctx.instance["version"]}"
		buffer = bytearray()
		response = pycurl.Curl()
		response.setopt(response.URL, url)
		response.setopt(response.CAINFO, certifi.where())
		response.setopt(response.WRITEFUNCTION, lambda d: buffer.extend(d))
		response.perform()
		queryData = json.loads(buffer.decode("utf-8"))
		response.close()

		cache.setAPICache(ctx, "hangarsearch.db", query, queryData)

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


