# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606
import os, toml, instance

def mcmm(slug, mod_data):
	if not os.path.exists(os.path.expanduser(f"{instance.instance_dir}/.content/")):
		os.makedirs(os.path.expanduser(f"{instance.instance_dir}/.content/"))
	print(f"Indexing mod '{slug}'")
	index = {}
	index['index-version'] = 1
	index['filename'] = mod_data['files'][0]['filename']
	index['slug'] = slug
	index['mod-id'] = mod_data["project_id"]
	index['version'] = mod_data["version_number"]
	index['version-id'] = mod_data["id"]
	index['hash'] = mod_data['files'][0]['hashes']['sha512']
	index['hash-format'] ='sha512'
	index['mode'] = 'url'
	index['url'] = mod_data["files"][0]["url"]
	index['source'] ='modrinth'
	index['game-version'] = instance.minecraft_version
	index['reason'] = "explicit"
	toml.dump(index, open(f"{instance.instance_dir}/.content/{slug}.mm.toml", 'w',  encoding='utf-8'))
	if "index-compatibility" in instance.instancecfg and instance.instancecfg["index-compatibility"] == "prism":
		prism(slug, mod_data)

def prism(slug, mod_data):
	if not os.path.exists(os.path.expanduser(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/.index")):
		os.makedirs(os.path.expanduser(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/.index"))
	cache_data = toml.load(f"{instance.cachedir}/modrinth-api/{slug}.mm.toml")["mod-api"]
	index = {}
	index["filename"] = mod_data["files"][0]["filename"]
	index["name"] = cache_data["title"]
	if cache_data["client_side"] != "unsupported" and cache_data["server_side"] != "unsupported":
		index["side"] = "both"
	elif cache_data["client_side"] == "unsupported":
		index["side"] = "server"
	elif cache_data["server_side"] == "unsupported":
		index["side"] = "client"
	index["download"] = {}
	index["download"]["hash"] = mod_data["files"][0]["hashes"]["sha512"]
	index["download"]["hash-format"] = "sha512"
	index["download"]["mode"] = "url"
	index["download"]["url"] = mod_data["files"][0]["url"]
	index["update"] = {"modrinth": {"mod-id": mod_data["project_id"] ,"version": mod_data["id"]}}
	index = toml.dumps(index)[:-1]
	index = index.replace('"', "'")
	with open(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/.index/{slug}.pw.toml", 'w',  encoding='utf-8') as file:
		file.write(index)
