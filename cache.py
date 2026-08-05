"""
cache related functions
"""

import logger as logging
from time import time
import os, sqlite3, json
_copyfile = None

APICACHEVERSION = 6
_preserve = {}

logger = logging.getLogger()

def isAPICached(ctx, db: str, slug: str) -> bool:
	db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
	if slug in _preserve and _preserve[slug] == False:
		return False
	try:
		cacheData = db.execute("SELECT * FROM cachev6 WHERE slug=?", (slug,)).fetchone()
		if cacheData is None:
			cacheData = db.execute("SELECT * FROM cachev6 WHERE id=?", (slug,)).fetchone()
		if cacheData is None:
			db.close()
			return False
	except sqlite3.OperationalError as e:
		logger.warning(e)
		return False
	valid = time() - cacheData[3] <= ctx.config["api-expire"] and cacheData[2] == APICACHEVERSION
	_preserve[cacheData[0]] = json.loads(cacheData[4]) if valid else False
	_preserve[cacheData[1]] = _preserve[cacheData[0]]
	db.close()
	return valid
	
def isModCached(ctx, filename: str) -> bool:
	global _copyfile
	if _copyfile is None:
		from shutil import copyfile as _copyfile
	return os.path.exists(os.path.join(ctx.config["cache-dir"], "mods", filename))

def getAPICache(ctx, db: str, slug: str) -> dict:
	if not isAPICached(ctx, db, slug):
		return False
	if slug in _preserve:
		cacheData = _preserve[slug]
	else:
		db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
		cacheData = json.loads(db.execute("SELECT * FROM cachev6 WHERE slug=?", (slug,)).fetchone()[3])
		db.close()
	return cacheData

def getModCache(ctx, path: str, dest: str) -> bool:
	if not isModCached(ctx, path):
		return False
	_copyfile(os.path.join(ctx.config["cache-dir"], "mods", path), os.path.join(ctx.instanceDir, dest))
	return True

def setAPICache(ctx, db: str, id: str, slug: str, apiData: dict):
	db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], db))
	db.execute("""CREATE TABLE IF NOT EXISTS
		cachev6(id TEXT PRIMARY KEY, slug TEXT, apicacheversion INTEGER, time FLOAT, data TEXT)""")
	db.execute("""INSERT OR REPLACE INTO cachev6 VALUES
		(?, ?, ?, ?, ?)""", (id, slug, APICACHEVERSION, time(), json.dumps(apiData)))
	db.commit()
	db.close()

def setModCache(ctx, path: str, dest: str):
	if isModCached(ctx, dest):
		return
	_copyfile(os.path.join(ctx.instanceDir, path), os.path.join(ctx.config["cache-dir"], "mods", dest))

def clearCache(ctx, sources):
	if ctx.args["suboperation"] in ["content", "all"]:
		clearModCache(ctx)
	if ctx.args["suboperation"] in ["api", "all"]:
		clearAPICache(ctx, sources)
		return
	for source in [sources[source] for source in sources if hasattr(sources[source], "DB")]:
		db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], source.DB))
		db.execute("DELETE FROM cachev6 WHERE time < ?", (time() - 3600,))
		db.commit()
		db.close()
		logger.info("cache cleared from %s", os.path.join(ctx.config["cache-dir"], source.DB))
	
	print("Done Clearing Cache")

def clearAPICache(ctx, sources):
	if not ctx.args["noconfirm"]:
		print("Are you sure you want to clear all api cache?\nThis action cannot be undone\n")
		yn = input(":: Proceed with clearing all api cache? [Y/n]: ")
		print("")
		if yn.lower() != 'y' and yn != '':
			return
	for source in [sources[source] for source in sources if hasattr(sources[source], "DB")]:
		db = sqlite3.connect(os.path.join(ctx.config["cache-dir"], source.DB))
		db.execute("DELETE FROM cachev6")
		db.commit()
		db.close()
		logger.info("cache cleared from %s", os.path.join(ctx.config["cache-dir"], source.DB))
	print("Done Clearing Cache")

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
		logger.info("Deleted content cache for %s (clear content cache)", file)
