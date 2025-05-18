"""
cache related functions
"""

from shutil import copyfile
from time import time
import logging, os, toml, commons

APICACHEVERSION = 3

def isAPICached(filename: str, source: str):
	filename = filename.split(".")[0]
	path = os.path.join(commons.cacheDir, f"{source}-api", f"{filename}.{f'{source}query' if commons.args['operation'] == 'search' else 'mmcache'}.toml")
	if not os.path.exists(path):
		return False
	cacheData = toml.load(path)
	return time() - cacheData["time"] <= commons.config["api-expire"] and cacheData["api-cache-version"] == APICACHEVERSION

def isModCached(slug: str, loader: str, mod_version: str, game_version: str):
	return os.path.exists(os.path.join(commons.cacheDir, "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"))

def getAPICache(slug: str, source: str):
	if not isAPICached(slug, source):
		return False
	return toml.load(os.path.join(commons.cacheDir, f"{source}-api", f"{slug}.{f'{source}query' if commons.args['operation'] == 'search' else 'mmcache'}.toml"))["api"]

def getModCache(slug: str, loader: str, mod_version: str, game_version: str, folder: str, filename: str):
	if not isModCached(slug, loader, mod_version, game_version):
		return False
	copyfile(os.path.join(commons.cacheDir, "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"), os.path.join(commons.instance_dir, folder, filename))
	return True

def setAPICache(slug: str, apiData: dict, source: str):
	path = os.path.join(commons.cacheDir, f"{source}-api", f"{slug}.{f'{source}query' if commons.args['operation'] == 'search' else 'mmcache'}.toml")
	cacheData = {"time": time(), "api-cache-version": APICACHEVERSION, "api": apiData}
	logger.info(f"Caching data for {'query' if commons.args['operation'] == 'search' else 'mod'} '%s' to %s", slug, path)
	if slug in commons.args["query" if commons.args['operation'] == "search" else "slugs"]:
		print(f"Caching data for {'query' if commons.args['operation'] == 'search' else 'mod'} '{slug}'")
	with open(path, "w", encoding="utf-8") as f:
		toml.dump(cacheData, f)

def setModCache(slug: str, loader: str, mod_version: str, game_version: str, folder: str, filename: str):
	if isModCached(slug, loader, mod_version, game_version):
		return
	copyfile(os.path.join(commons.instance_dir, folder, filename), os.path.join(commons.cacheDir, "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"))

def clearCache():
	if not os.listdir(os.path.join(commons.cacheDir, "modrinth-api")):
		return
	for file in os.listdir(os.path.join(commons.cacheDir, "modrinth-api")):
		cacheData = toml.load(os.path.join(commons.cacheDir, "modrinth-api", file))
		if time() - cacheData["time"] > commons.config["api-expire"] or cacheData["api-cache-verison"] != APICACHEVERSION:
			os.remove(os.path.join(os.path.join(commons.cacheDir, "modrinth-api")))
			logger.info("Deleted cache for %s because it has expired", file.split('.')[0])
			print(f"Deleted api cache for {file.split('.')[0]} (expired)")
	if commons.args["suboperation"] in ["api", "all"]:
		clearAPICache()
	if commons.args["suboperation"] in ["content", "all"]:
		clearModCache()
	print("Done Clearing Cache")

def clearAPICache():
	if not os.listdir(os.path.join(commons.cacheDir, "modrinth-api")):
		return
	if not commons.args["auto-confirm"]:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return
	for file in os.listdir(os.path.join(commons.cacheDir, "modrinth-api")):
		os.remove(os.path.join(commons.cacheDir, "modrinth-api", file))
		print(f"Deleted api cache for {file.split('.')[0]}")
		logger.info("Deleted api cache for %s (clear all)", file.split('.')[0])

def clearModCache():
	if not os.listdir(os.path.join(commons.cacheDir, "mods")):
		return
	if not commons.args["auto-confirm"]:
		print("Are you sure you want to clear content cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing content cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return
	for file in os.listdir(f"{commons.cacheDir}/mods"):
		os.remove(os.path.join(commons.cacheDir, commons.instancecfg["modfolder"], file))
		print(f"Deleted content cache for {file}")
		logger.info("Deleted content cache for %s (clear content cache)", {file})

logger = logging.getLogger(__name__)
