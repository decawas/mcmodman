"""
handles indexing for content
"""
import logging, os, tomlkit, commons
from configobj import ConfigObj

logger = logging.getLogger(__name__)

def mcmm(slug, mod_data, reason="explicit", source="local"):
	if not os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, ".content"))):
		os.makedirs(os.path.expanduser(os.path.join(commons.instance_dir, ".content")))
	print(f"Indexing mod '{slug}'")

	index = ConfigObj(unrepr=True)
	index['index-version'] = 3
	index['filename'] = mod_data['versions'][0]['files'][0]['filename']
	index['slug'] = slug
	index['mod-id'] = mod_data.get("id") or mod_data.get("projectID")
	index['version'] = mod_data['versions'][0]["version_number"]
	index['version-id'] = mod_data["versions"][0]["id"]
	index['type'] = mod_data['versions'][0].get("type", "")
	index['folder'] = os.path.expanduser(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"]))
	index['source'] = source
	index['game-version'] = commons.minecraft_version
	index['reason'] = reason

	index.filename = os.path.join(commons.instance_dir, ".content", f"{slug}.mm.ini")
	index.write()
	logger.debug("index %s for mod '%s' written to %s", dict(index), slug, index.filename)

	if "index-compatibility" in commons.instancecfg and commons.instancecfg["index-compatibility"] == "packwiz" and mod_data["project_type"] == "mod" and source != "local":
		packwiz(slug, mod_data)

def packwiz(slug, mod_data):
	if not os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index"))):
		os.makedirs(os.path.expanduser(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index")))
	index = {"filename": mod_data['versions'][0]['files'][0]['filename'], "name": mod_data["title"]}
	index["download"] = {"hash": mod_data['versions'][0]["files"][0]["hashes"]["sha512"], "hash-format": "sha512", "mode": "url", "url": mod_data['versions'][0]["files"][0]["url"]}
	index["update"] = {"modrinth": {"mod-id": mod_data["id"] ,"version": mod_data["id"]}}

	index["side"] = "both"
	if mod_data["client_side"] == "unsupported":
		index["side"] = "server"
	elif mod_data["server_side"] == "unsupported":
		index["side"] = "client"
	index = tomlkit.dumps(index)[:-1]
	with open(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index", f"{slug}.pw.toml"), 'w',  encoding='utf-8') as file:
		logger.debug("index %s for mod '%s' written to %s", index, slug, os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index", f"{slug}.pw.toml"))
		file.write(index)

def get(slug, reason="explicit"):
	if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.ini")):
		index = ConfigObj(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.ini"), unrepr=True)
		logger.info("Loaded index for mod '%s'", slug)
		return dict(index)
	elif os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml")):
		with open(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"), "r", encoding="utf-8") as f:
			index = tomlkit.load(f)
		logger.info("Loaded index for mod '%s' (legacy)", slug)
		return index
	elif commons.args["operation"] in ["sync", "downgrade"]:
		index = {"slug": slug, "filename": "-", "version": "None", "version-id": "None", "reason": reason}
		logger.info("Created dummy index for new mod '%s'", slug)
		return index
	return None
