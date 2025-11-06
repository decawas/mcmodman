"""
cache related functions
"""

from shutil import copyfile
from time import time
import logging, os, configobj, sqlite3, json

APICACHEVERSION = 5
preserve = {}

def isAPICached(ctx, db: str, slug: str) -> bool:
	db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
	try:
		cacheData = db.execute("SELECT * FROM cache WHERE slug=?", (slug,)).fetchone()
	except sqlite3.OperationalError:
		return False
	if cacheData is None:
		return False
	preserve[slug] = json.loads(cacheData[3])
	db.close()
	return time() - cacheData[2] <= ctx.config["api-expire"] and cacheData[1] == APICACHEVERSION
	
def isModCached(ctx, slug: str, loader: str, mod_version: str, game_version: str) -> bool:
	return os.path.exists(os.path.join(ctx.config["cache-dir"], "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"))

def getAPICache(ctx, db: str, slug: str) -> dict:
	if not isAPICached(ctx, db, slug):
		return False
	db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
	if slug in preserve:
		cacheData = preserve[slug]
	else:
		db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
		cacheData = json.loads(db.execute("SELECT * FROM cache WHERE slug=?", (slug,)).fetchone()[3])
		db.close()
	return cacheData

def getModCache(ctx, slug: str, loader: str, mod_version: str, game_version: str, folder: str, filename: str) -> bool:
	if not isModCached(ctx, slug, loader, mod_version, game_version):
		return False
	copyfile(os.path.join(ctx.config["cache-dir"], "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"), os.path.join(ctx.instanceDir, folder, filename))
	return True

def setAPICache(ctx, db: str, slug: str, apiData: dict):
	db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
	db.execute("""CREATE TABLE IF NOT EXISTS
		cache(slug TEXT PRIMARY KEY, apicacheversion INTEGER, time FLOAT, data TEXT)""")
	db.execute("""INSERT OR REPLACE INTO cache VALUES
		(?, ?, ?, ?)""", (slug, APICACHEVERSION, time(), json.dumps(apiData)))
	db.commit()
	db.close()

def setModCache(ctx, slug: str, loader: str, mod_version: str, game_version: str, folder: str, filename: str):
	if isModCached(ctx, slug, loader, mod_version, game_version):
		return
	copyfile(os.path.join(ctx.instanceDir, folder, filename), os.path.join(ctx.config["cache-dir"], "mods", f"{slug}-{loader}-{mod_version}-{game_version}.jar"))

def clearCache(ctx):
	if ctx.args["suboperation"] in ["api", "all"]:
		clearAPICache(ctx)
	if ctx.args["suboperation"] in ["content", "all"]:
		clearModCache(ctx)
	if not any([os.listdir(os.path.join(ctx.config["cache-dir"], "modrinth-api")), os.listdir(os.path.join(ctx.config["cache-dir"], "hangar-api"))]):
		return
	for source in ["modrinth", "hangar"]:
		for file in os.listdir(os.path.join(ctx.config["cache-dir"], f"{source}-api")):
			cacheData = configobj.ConfigObj(os.path.join(ctx.config["cache-dir"], f"{source}-api", file), unrepr=True, encoding='utf-8')
			if time() - cacheData["time"] > ctx.config["api-expire"] or cacheData.get("api-cache-version", 0) != APICACHEVERSION:
				os.remove(os.path.join(ctx.config["cache-dir"], f"{source}-api", file))
				logger.info("Deleted cache for %s because it has expired", file.split('.')[0])
				print(f"Deleted api cache for {file.split('.')[0]} (expired)")
	print("Done Clearing Cache")

def clearAPICache(ctx):
	if not any([os.listdir(os.path.join(ctx.config["cache-dir"], "modrinth-api")), os.listdir(os.path.join(ctx.config["cache-dir"], "hangar-api"))]):
		return
	if not ctx.args["noconfirm"]:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return
	for source in ["modrinth", "hangar"]:
		for file in os.listdir(os.path.join(ctx.config["cache-dir"], f"{source}-api")):
			os.remove(os.path.join(ctx.config["cache-dir"], f"{source}-api", file))
			print(f"Deleted api cache for {file.split('.')[0]}")
			logger.info("Deleted api cache for %s (clear all)", file.split('.')[0])

def clearModCache(ctx):
	if not os.listdir(os.path.join(ctx.config["cache-dir"], "mods")):
		return
	if not ctx.args["noconfirm"]:
		print("Are you sure you want to clear content cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing content cache? [y/N]: ")
		print("")
		if yn.lower() != 'y':
			return
	for file in os.listdir(os.path.join(ctx.config["cache-dir"], "mods")):
		os.remove(os.path.join(ctx.config["cache-dir"], "mods", file))
		print(f"Deleted content cache for {file}")
		logger.info("Deleted content cache for %s (clear content cache)", {file})

logger = logging.getLogger(__name__)
