# pylint: disable=E0601 disable=C0114 disable=C0115 disable=C0116 disable=C0411 disable=C0103 disable=W0707 disable=C0410 disable=C0321
import os, toml

def mcmm(slug, mod_data):
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
	index['game-version'] = minecraft_version
	index['reason'] = "explicit"
	toml.dump(index, open(f"{instance_dir}/mods/.index/{slug}.mm.toml", 'w',  encoding='utf-8'))
	if "index-compatibility" in instancecfg and instancecfg["index-compatibility"] == "prism":
		prism(slug, mod_data)

def prism(slug, mod_data):
	cache_data = toml.load(f"{cachedir}/modrinth-api/{slug}.mm.toml")["mod-api"]
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
	with open(f"{instance_dir}/mods/.index/{slug}.pw.toml", 'w',  encoding='utf-8') as file:
		file.write(index)

if os.path.exists(os.path.expanduser("~/.config/ekno/mcmodman/config.toml")):
	config = toml.load(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"))
else:
	config = {"instances": [{"name": ".minecraft", "path": "~/.minecraft", "id": "0"}], "cache-dir": "autodetect", "include-beta": False, "api-expire": 3600, "checksum": "Always"}
	os.makedirs(os.path.expanduser("~/.config/ekno/mcmodman"))
	toml.dump(config, open(os.path.expanduser("~/.config/ekno/mcmodman/config.toml"), 'w',  encoding='utf-8'))

if config['cache-dir'] == "autodetect":
	cachedir = os.path.expanduser("~/.cache/mcmodman")
elif config['cache-dir'] != "autodetect":
	cachedir = os.path.expanduser(config['cache-dir'])
if not os.path.exists(cachedir):
	os.makedirs(cachedir)
	os.makedirs(f"{cachedir}/mods")
	os.makedirs(f"{cachedir}/modrinth-api")

instance_dir = config["instances"][0]["path"]

if os.path.exists(f"{instance_dir}/mcmodman_managed.toml"):
	instancecfg = toml.load(f"{instance_dir}/mcmodman_managed.toml")
	minecraft_version = instancecfg["version"]
else:
	minecraft_version = ""
