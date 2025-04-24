"""
cache related functions
"""

from shutil import copyfile
from time import time
import logging, os, toml, commons

APICACHEVERSION = 2

def isAPICached(filename):
	filename = filename.split(".")[0]
	path = os.path.join(commons.cacheDir, "modrinth-api", f"{filename}.{'modrinthquery' if commons.args['operation'] == 'search' else 'mmcache'}.toml")
	if not os.path.exists(path):
		return False
	cacheData = toml.load(path)
	if time() - cacheData["time"] > commons.config["api-expire"] or cacheData["api-cache-version"] != APICACHEVERSION:
		return False
	return True

def isModCached(f):
	return os.path.exists(os.path.join(commons.cacheDir, "mods", f))

def getAPICache(slug):
	if not isAPICached(slug):
		return False
	return toml.load(os.path.join(commons.cacheDir, "modrinth-api", f"{slug}.{'modrinthquery' if commons.args['operation'] == 'search' else 'mmcache'}.toml"))["query-api" if commons.args['operation'] == 'search' else "mod-api"]

def getModCache(filename, folder):
	if not isModCached(filename):
		return False
	copyfile(os.path.join(commons.cacheDir, "mods", filename), os.path.join(commons.instance_dir, folder, filename))
	return True

def setAPICache(slug, apiData):
	path = os.path.join(commons.cacheDir, "modrinth-api", f"{slug}.{'modrinthquery' if commons.args['operation'] == 'search' else 'mmcache'}.toml")
	cacheData = {"time": time(), "api-cache-version": APICACHEVERSION, "mod-api": apiData}
	logger.info(f"Caching data for {'query' if commons.args['operation'] == 'search' else 'mod'} '%s' to %s", slug, path)
	if slug in commons.args["slugs"]:
		print(f"Caching data for {'query' if commons.args['operation'] == 'search' else 'mod'} '{slug}'")
	with open(path, "w", encoding="utf-8") as f:
		toml.dump(cacheData, f)

def setModCache(filename, folder):
	if isModCached(filename):
		return
	copyfile(os.path.join(commons.instance_dir, folder, filename), os.path.join(commons.cacheDir, "mods", filename))

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
