"""
handles indexing for content
"""
import logging, os, tomlkit, commons

logger = logging.getLogger(__name__)

def mcmm(slug, mod_data, reason="explicit", source="local"):
	if not os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, ".content"))):
		os.makedirs(os.path.expanduser(os.path.join(commons.instance_dir, ".content")))
	print(f"Indexing mod '{slug}'")
	index = {'index-version': 2, 'filename': mod_data['versions'][0]['files'][0]['filename'], 'slug': slug, 'mod-id': mod_data.get("id" or "projectID"), 'version': mod_data['versions'][0]["version_number"], 'version-id': mod_data["versions"][0]["id"], "type": mod_data['versions'][0].get("type", ""), "folder": os.path.expanduser(os.path.join(commons.instance_dir, mod_data['versions'][0]["folder"])), 'source': source, 'game-version': commons.minecraft_version, 'reason': reason}

	with open(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"), 'w',  encoding='utf-8') as f:
		f.write(tomlkit.dumps(index))
		logger.debug("index %s for mod '%s' written to %s", index, slug, os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"))
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
	if os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml")):
		with open(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"), "r", encoding="utf-8") as f:
			index = tomlkit.load(f)
		logger.info("Loaded index for mod '%s'", slug)
		return index
	elif commons.args["operation"] in ["sync", "downgrade"] and not os.path.exists(os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml")):
		index = {"slug": {slug}, "filename": "-", "version": "None", "version-id": "None", "reason": reason}
		logger.info("Created dummy index for new mod '%s'", slug)
		return index
	return None
