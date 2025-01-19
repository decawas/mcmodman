# pylint: disable=C0114 C0116 C0410
import os, toml, commons, modrinth

def mcmm(slug, mod_data):
	if not os.path.exists(os.path.expanduser(f"{commons.instance_dir}/.content/")):
		os.makedirs(os.path.expanduser(f"{commons.instance_dir}/.content/"))
	print(f"Indexing mod '{slug}'")
	_, folder = modrinth.project_get_type(mod_data)
	if folder == "":
		with open("server.properties", "r", encoding="utf-8") as f:
			properties = toml.loads(f.read())
		folder = os.path.join(properties["level-name"], "datapacks")
	print(mod_data["versions"][0]["id"])
	index = {'index-version': 2, 'filename': mod_data['versions'][0]['files'][0]['filename'], 'slug': slug, 'mod-id': mod_data["id"], 'version': mod_data['versions'][0]["version_number"], 'version-id': mod_data["versions"][0]["id"], "type": mod_data["project_type"], "folder": folder, 'hash': mod_data['versions'][0]['files'][0]['hashes']['sha512'], 'hash-format': 'sha512', 'mode': 'url', 'url': mod_data['versions'][0]["files"][0]["url"], 'source': 'modrinth', 'game-version': commons.minecraft_version, 'reason': "explicit"}
	if commons.instancecfg["loader"] in mod_data["loaders"]:
		pass
	elif "datapack" in mod_data["loaders"]:
		index["type"] = "datapack"

	with open(f"{commons.instance_dir}/.content/{slug}.mm.toml", 'w',  encoding='utf-8') as f:
		toml.dump(index, f)
	if "index-compatibility" in commons.instancecfg and commons.instancecfg["index-compatibility"] == "packwiz" and mod_data["project_type"] == "mod":
		packwiz(slug, mod_data)

def packwiz(slug, mod_data):
	if not os.path.exists(os.path.expanduser(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index"))):
		os.makedirs(os.path.expanduser(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], ".index")))
	index = {"filename": mod_data["files"][0]["filename"], "name": mod_data["title"]}
	index["download"] = {"hash": mod_data["files"][0]["hashes"]["sha512"], "hash-format": "sha512", "mode": "url", "url": mod_data["files"][0]["url"]}
	index["update"] = {"modrinth": {"mod-id": mod_data["project_id"] ,"version": mod_data["id"]}}

	index["side"] = "both"
	if mod_data["client_side"] == "unsupported":
		index["side"] = "server"
	elif mod_data["server_side"] == "unsupported":
		index["side"] = "client"
	index = toml.dumps(index)[:-1]
	with open(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], f"index/{slug}.pw.toml"), 'w',  encoding='utf-8') as file:
		file.write(index)
