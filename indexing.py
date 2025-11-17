"""
handles indexing for content
"""
import logging, os, time
from configobj import ConfigObj # type: ignore

logger = logging.getLogger(__name__)

INDEX_VERSION = 5

def mcmm(ctx, slug, mod_data, reason="explicit", source="local"):
	if not os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, ".content"))):
		os.makedirs(os.path.expanduser(os.path.join(ctx.instanceDir, ".content")))

	index = ConfigObj(unrepr=True, encoding='utf-8')
	index['index-version'] = INDEX_VERSION
	index['files'] = mod_data["versions"][0]["filepaths"]
	index['slug'] = slug
	index['mod-id'] = mod_data.get("id") or mod_data.get("projectID")
	index['version'] = mod_data['versions'][0]["version_number"]
	index['version-id'] = mod_data["versions"][0]["id"]
	index['type'] = mod_data['versions'][0].get("type", "")
	index['source'] = source
	index['game-version'] = ctx.instance["version"]
	index['description'] = mod_data.get("description", "Description Not Provided")
	if source == "modrinth":
		index['loader'] = mod_data['versions'][0]["loaders"][0] if ctx.instance["loader"] not in mod_data['versions'][0]["loaders"] else ctx.instance["loader"]
	elif source == "hangar":
		index['loader'] = ctx.instance["loader"]
	index['filesize'] = mod_data['versions'][0]['files'][0]["size"] if "files" in mod_data['versions'][0] else 0
	index['date'] = time.ctime()
	index['reason'] = reason

	index.filename = os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.ini")
	index.write()
	logger.debug("index %s for mod '%s' written to %s", dict(index), slug, index.filename)

	if "index-compatibility" in ctx.instance and ctx.instance["index-compatibility"] == "packwiz" and mod_data["project_type"] == "mod" and source in ["modrinth"]:
		packwiz(ctx, slug, mod_data)

def packwiz(ctx, slug, mod_data):
	import tomlkit
	if not os.path.exists(os.path.expanduser(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index"))):
		os.makedirs(os.path.expanduser(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index")))
	index = {"filename": mod_data['versions'][0]['files'][0]['filename'], "name": mod_data["title"]}
	index["download"] = {"hash": mod_data['versions'][0]["files"][0]["hashes"]["sha512"], "hash-format": "sha512", "mode": "url", "url": mod_data['versions'][0]["files"][0]["url"]}
	index["update"] = {"modrinth": {"mod-id": mod_data["id"] ,"version": mod_data["id"]}}

	index["side"] = "both"
	if mod_data["client_side"] == "unsupported":
		index["side"] = "server"
	elif mod_data["server_side"] == "unsupported":
		index["side"] = "client"
	index = tomlkit.dumps(index)[:-1]
	with open(os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index", f"{slug}.pw.toml"), 'w',  encoding='utf-8') as file:
		logger.debug("index %s for mod '%s' written to %s", index, slug, os.path.join(ctx.instanceDir, ctx.instance["modfolder"], ".index", f"{slug}.pw.toml"))
		file.write(index)

def get(ctx, slug, reason="explicit") -> dict:
	if os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.ini")):
		index = ConfigObj(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.ini"), unrepr=True, encoding='utf-8')
		logger.info("Loaded index for mod '%s'", slug)
		return dict(index)
	elif os.path.exists(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.toml")):
		import tomlkit
		with open(os.path.join(ctx.instanceDir, ".content", f"{slug}.mm.toml"), "r", encoding="utf-8") as f:
			index = tomlkit.load(f)
		logger.info("Loaded index for mod '%s' (legacy)", slug)
		return index
	elif ctx.args["operation"] in ["sync", "downgrade"]:
		index = {"index-version": 2147483647, "slug": slug, "files": [], "version": "None", "version-id": "None", "reason": reason, "size": 0}
		logger.info("Created dummy index for new mod '%s'", slug)
		return index
	return None
