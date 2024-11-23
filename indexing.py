# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606 W1203 I1101
import os, toml, commons

def mcmm(slug, mod_data):
	if not os.path.exists(os.path.expanduser(f"{commons.instance_dir}/.content/")):
		os.makedirs(os.path.expanduser(f"{commons.instance_dir}/.content/"))
	print(f"Indexing mod '{slug}'")
	index = {'index-version': 1, 'filename': mod_data['files'][0]['filename'], 'slug': slug, 'mod-id': mod_data["project_id"], 'version': mod_data["version_number"], 'version-id': mod_data["id"], 'hash': mod_data['files'][0]['hashes']['sha512'], 'hash-format': 'sha512', 'mode': 'url', 'url': mod_data["files"][0]["url"], 'source': 'modrinth', 'game-version': commons.minecraft_version, 'reason': "explicit"}
	toml.dump(index, open(f"{commons.instance_dir}/.content/{slug}.mm.toml", 'w',  encoding='utf-8'))
	if "index-compatibility" in commons.instancecfg and commons.instancecfg["index-compatibility"] == "prism":
		prism(slug, mod_data)

def prism(slug, mod_data):
	if not os.path.exists(os.path.expanduser(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/.index")):
		os.makedirs(os.path.expanduser(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/.index"))
	cache_data = toml.load(f"{commons.cache_dir}/modrinth-api/{slug}.mm.toml")["mod-api"]
	index = {"filename": mod_data["files"][0]["filename"], "name": cache_data["title"]}
	index["download"] = {"hash": mod_data["files"][0]["hashes"]["sha512"], "hash-format": "sha512", "mode": "url", "url": mod_data["files"][0]["url"]}
	index["update"] = {"modrinth": {"mod-id": mod_data["project_id"] ,"version": mod_data["id"]}}

	index["side"] = "both"
	if cache_data["client_side"] == "unsupported":
		index["side"] = "server"
	elif cache_data["server_side"] == "unsupported":
		index["side"] = "client"
	index = toml.dumps(index)[:-1]
	with open(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/.index/{slug}.pw.toml", 'w',  encoding='utf-8') as file:
		file.write(index)

#TODO: add dual indexing for modrinth
