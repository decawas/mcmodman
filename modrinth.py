# pylint: disable=E0601 disable=C0114 disable=C0115 disable=C0116 disable=C0411 disable=C0103 disable=W0707 disable=C0410 disable=C0321
import hashlib, os, requests, toml, time
def get_mod(slug, mod_data, index):
	if os.path.exists(f"{cachedir}/mods/{mod_data['files'][0]['filename']}.mm.toml"):
		print(f"Using cached version for mod '{slug}'")
		os.system(f"cp {cachedir}/mods/{mod_data['files'][0]['filename']} {instance_dir}/mods/")
		os.system(f"cp {cachedir}/mods/{mod_data['files'][0]['filename']}.mm.toml {instance_dir}/mods/.index/{slug}.mm.toml")
	else:
		print(f"Downloading mod '{slug}'")
		url = f"{mod_data['files'][0]['url']}"
		os.system(f"wget {url} -O {instance_dir}/mods/{mod_data["files"][0]["filename"]} -o /tmp/wget")
	if config["checksum"] in ["Always", "Download"] and not os.path.exists(f"{cachedir}/mods/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif config["checksum"] == "Always" and os.path.exists(f"{cachedir}/mods/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif config["checksum"] == "Never" and not os.path.exists(f"{cachedir}/mods/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = False
	else: perfcheck = True
	if perfcheck:
		print("Checking hash")
		checksum = hashlib.sha512(open(f"{instance_dir}/mods/{mod_data['files'][0]['filename']}", 'rb').read()).hexdigest()
		if mod_data["files"][0]["hashes"]["sha512"] != checksum:
			print("Failed to validate file")
			os.system(f"rm {instance_dir}/mods/{mod_data['files'][0]['filename']}")
		return "Bad checksum"
	if os.path.exists(f"{instance_dir}/mods/{index['filename']}"):
		print("Removing old version")
		os.system(f"rm -rf {instance_dir}/mods/{index['filename']}")

def parse_api(api_data):
	matches = []
	if config["include-beta"]:
		allowed_version_types = ["release", "beta", "alpha"]
	else:
		allowed_version_types = ["release"]
		for version in api_data:
			if version["version_type"] in allowed_version_types and minecraft_version in version["game_versions"] and mod_loader in version["loaders"]:
				matches.append(version)
	if not matches:
		print("No matching versions found")
		return "No version"
	elif matches:
		return matches


def get_api(slug):
	if os.path.exists(f"{cachedir}/modrinth-api/{slug}.mm.toml"):
		cache_data = toml.load(f"{cachedir}/modrinth-api/{slug}.mm.toml")
		if time.time() - cache_data["time"] < config["api-expire"] and cache_data["api-cache-version"] == 1:
			print("Using cached api data")
			mod_data = cache_data["mod-api"]
			version_data = cache_data["version-api"]
		else:
			del cache_data
	if "cache_data" not in locals():
		print("Fetching api data")
		url = f"https://api.modrinth.com/v2/project/{slug}"
		response = requests.get(url, headers={'User-Agent': 'discord: .ekno (there is a . dont forget it), github: no github repo just yet sorry'}, timeout=30)
		try:
			response.raise_for_status()
		except:
			print(f"Mod '{slug}' not found")
			raise SystemExit
		mod_data = response.json()
		url = f"https://api.modrinth.com/v2/project/{slug}/version"
		response = requests.get(url, headers={'User-Agent': 'discord: .ekno (there is a . dont forget it), github: no github repo just yet sorry'}, timeout=30)
		response.raise_for_status()
		version_data = response.json()

		cache_data = {"time": time.time(), "api-cache-version": 1, "mod-api": mod_data, "version-api": version_data}
		with open(f"{cachedir}/modrinth-api/{slug}.mm.toml", 'w',  encoding='utf-8') as file:
			print("Caching api data")
			toml.dump(cache_data, file)

	return [mod_data, version_data]

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
	mod_loader = instancecfg["loader"]
	minecraft_version = instancecfg["version"]
else:
	mod_loader = ""
	minecraft_version = ""
