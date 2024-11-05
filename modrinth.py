# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606
import hashlib, os, requests, toml, time, instance
def get_mod(slug, mod_data, index):
	if os.path.exists(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"):
		print(f"Using cached version for mod '{slug}'")
		os.system(f"cp {instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']} {instance.instance_dir}/{instance.instancecfg["modfolder"]}/")
		os.system(f"cp {instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml {instance.instance_dir}/.content/{slug}.mm.toml")
	else:
		print(f"Downloading mod '{slug}'")
		url = f"{mod_data['files'][0]['url']}"
		os.system(f"wget {url} -O {instance.instance_dir}/{instance.instancecfg["modfolder"]}/{mod_data["files"][0]["filename"]} -o /tmp/wget")
	if instance.config["checksum"] in ["Always", "Download"] and not os.path.exists(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif instance.config["checksum"] == "Always" and os.path.exists(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif instance.config["checksum"] == "Never" and not os.path.exists(f"{instance.cachedir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = False
	else: perfcheck = True
	if perfcheck:
		print("Checking hash")
		checksum = hashlib.sha512(open(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}", 'rb').read()).hexdigest()
		if mod_data["files"][0]["hashes"]["sha512"] != checksum:
			print("Failed to validate file")
			os.remove(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}")
		return "Bad checksum"
	if os.path.exists(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}"):
		print("Removing old version")
		os.remove(f"{instance.instance_dir}/{instance.instancecfg["modfolder"]}/{index['filename']}")

def parse_api(api_data):
	if api_data["project_type"] == "modpack":
		print(f"{api_data["slug"]} is a modpack")
		return "Modpack"

	if api_data["project_type"] == "mod":
		if instance.instancecfg["loader"] in api_data["loaders"]:
			mod_loader = instance.instancecfg["loader"]
		elif "datapack" in api_data["loaders"]:
			mod_loader = "datapack"
			if not "server.properties" in os.listdir(f"{instance.instance_dir}"):
				print("currently, mcmodman only supports datapacks for servers")
				mod_loader = "none"
		else:
			mod_loader = "none"
	elif api_data["project_type"] == "shader" and "optifine" in api_data["loaders"]:
		mod_loader = "optifine"
		if not ("optifine.mm.toml" in os.listdir(f"{instance.instance_dir}/.content") and "iris.mm.toml" in os.listdir(f"{instance.instance_dir}/.content")):
			print(f"\033[1;33;40mCaution: shader '{api_data["slug"]}' requires optifine or iris but neither is installed\033[0;37;40m")
	elif api_data["project_type"] == "shader" and "canvas" in api_data["loaders"]:
		mod_loader = "canvas"
		if not "canvas.mm.toml" in os.listdir(f"{instance.instance_dir}/.content"):
			print(f"\033[1;33;40mCaution: shader '{api_data["slug"]}' requires canvas but canvas is not installed\033[0;37;40m")
	elif api_data["project_type"] == "shader" and "vanilla" in api_data["loaders"]:
		mod_loader = "vanilla"
	elif api_data["project_type"] == "resourcepack":
		mod_loader = "minecraft"

	matches = []
	if instance.config["include-beta"]: # TODO: replace include-beta with beta-priority
		allowed_version_types = ["release", "beta", "alpha"]
	else:
		allowed_version_types = ["release"]
	for version in api_data["versions"]:
		if version["version_type"] in allowed_version_types and instance.minecraft_version in version["game_versions"] and mod_loader in version["loaders"]:
			matches.append(version)
	if not matches:
		print("No matching versions found")
		return "No version"
	elif matches:
		return matches


def get_api(slug):
	if os.path.exists(f"{instance.cachedir}/modrinth-api/{slug}.mm.toml"):
		cache_data = toml.load(f"{instance.cachedir}/modrinth-api/{slug}.mm.toml")
		if time.time() - cache_data["time"] < instance.config["api-expire"] and cache_data["api-cache-version"] == 2:
			print(f"Using cached api data for mod '{slug}'")
			mod_data = cache_data["mod-api"]
		else:
			del cache_data
	if "cache_data" not in locals():
		print(f"Fetching api data for mod '{slug}'")
		url = f"https://api.modrinth.com/v2/project/{slug}"
		response = requests.get(url, headers={'User-Agent': 'discord: .ekno (there is a . dont forget it), github: no github repo just yet sorry'}, timeout=30)
		if response.status_code != 200:
			print(f"Mod '{slug}' not found")
			raise SystemExit
		mod_data = response.json()
		url = f"https://api.modrinth.com/v2/project/{slug}/version"
		response = requests.get(url, headers={'User-Agent': 'discord: .ekno (there is a . dont forget it), github: no github repo just yet sorry'}, timeout=30)
		response.raise_for_status()
		mod_data["versions"] = response.json()

		cache_data = {"time": time.time(), "api-cache-version": 2, "mod-api": mod_data}
		with open(f"{instance.cachedir}/modrinth-api/{slug}.mm.toml", 'w',  encoding='utf-8') as file:
			print(f"Caching api data for mod '{slug}'")
			toml.dump(cache_data, file)

	return mod_data
