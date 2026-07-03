"""
handles indexing for content
"""
import os, time
import logger as logging
from configobj import ConfigObj

logger = logging.getLogger()

INDEXVERSION = 6
_indexkeys = None

def mcmm(ctx, slug, mod_data, reason="explicit", source="local"):
	if not os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, ".content"))):
		os.makedirs(os.path.expanduser(os.path.join(ctx.instanceDir, ".content")))

	loader = ""
	if source == "modrinth":
		loader = mod_data['versions'][0]["loaders"][0] if ctx.instance["loader"] not in mod_data['versions'][0]["loaders"] else ctx.instance["loader"]
	elif source == "hangar":
		loader = ctx.instance["loader"]

	ctx.instanceDB.execute("""INSERT OR REPLACE INTO mods VALUES
	(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
	(slug, INDEXVERSION, " ".join(mod_data["versions"][mod_data["selectedversion"]]["filepaths"]), mod_data.get("id") or mod_data.get("projectID"), mod_data['versions'][mod_data["selectedversion"]]["version_number"], mod_data["versions"][mod_data["selectedversion"]]["id"], mod_data['versions'][mod_data["selectedversion"]].get("type", ""), source, ctx.instance["version"], loader, mod_data.get("description", "Description Not Provided"), mod_data['versions'][mod_data["selectedversion"]]['files'][0]["size"] if "files" in mod_data['versions'][mod_data["selectedversion"]] else 0, time.ctime(), reason, "[]", "[]"))
	ctx.instanceDB.commit()

	if "index-compatibility" in ctx.instance and ctx.instance["index-compatibility"] == "packwiz" and "mod" in mod_data["project_types"] and source in ["modrinth"]:
		packwiz(ctx, slug, mod_data)

def packwiz(ctx, slug, mod_data):
	import tomlkit
	if not os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index"))):
		os.makedirs(os.path.expanduser(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index")))
	index = {"filename": mod_data['versions'][0]['files'][0]['filename'], "name": mod_data["name"]}
	index["download"] = {"hash": mod_data['versions'][0]["files"][0]["hashes"]["sha512"], "hash-format": "sha512", "mode": "url", "url": mod_data['versions'][0]["files"][0]["url"]}
	index["update"] = {"modrinth": {"mod-id": mod_data["id"] ,"version": mod_data["id"]}}

	index["side"] = "client"
	index = tomlkit.dumps(index)[:-1]
	with open(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index", f"{slug}.pw.toml"), 'w',  encoding='utf-8') as file:
		logger.debug("index %s for mod '%s' written to %s", index, slug, os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index", f"{slug}.pw.toml"))
		file.write(index)

def get(ctx, slug, reason="explicit") -> dict:
	global _indexkeys
	if not _indexkeys:
		_indexkeys = [v[0].replace("hyphen", "-") for v in list(ctx.instanceDB.execute("SELECT name FROM pragma_table_info('mods');"))]
	indexfromdb = ctx.instanceDB.execute("SELECT * FROM mods WHERE slug=?", (slug,)).fetchone()
	if indexfromdb:
		indexfromdb = {k: v for k, v in zip(_indexkeys, indexfromdb)}
		return indexfromdb
	elif ctx.args["operation"] in ["sync", "downgrade"]:
		index = {"index-version": 2147483647, "slug": slug, "files": [], "version": "None", "version-id": "None", "reason": reason, "size": 0}
		logger.info("Created dummy index for new mod '%s'", slug)
		return index
	return None
