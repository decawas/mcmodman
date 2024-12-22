# pylint: disable=E0601 C0114 C0115 C0116 C0411 C0103 W0707 C0410 C0321 E0606 W1203 I1101
import os, toml, commons, logging
from hashlib import sha512
from time import time
from requests import get
from shutil import copyfile

def get_mod(slug, mod_data, index):
	if os.path.exists(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"):
		print(f"Using cached version for mod '{slug}'")
		copyfile(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}", f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}")
		copyfile(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml", f"{commons.instance_dir}/.content/{slug}.mm.toml")
	else:
		print(f"Downloading mod '{slug}'")
		url = f"{mod_data['files'][0]['url']}"
		response = get(url, headers={'User-Agent': 'github: https://https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		logger.info(f'Modrinth returned headers {response.headers}')
		if response.status_code != 200:
			logger.error(f'Modrinth download returned {response.status_code}')
			return None
		with open(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{mod_data["files"][0]["filename"]}", "wb") as f:
			f.write(response.content)
	if commons.config["checksum"] in ["Always", "Download"] and not os.path.exists(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif commons.config["checksum"] == "Always" and os.path.exists(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = True
	elif commons.config["checksum"] == "Never" and not os.path.exists(f"{commons.cache_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}.mm.toml"): perfcheck = False
	else: perfcheck = True
	if perfcheck:
		print("Checking hash")
		checksum = sha512(open(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}", 'rb').read()).hexdigest()
		if mod_data["files"][0]["hashes"]["sha512"] != checksum:
			print("Failed to validate file")
			os.remove(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{mod_data['files'][0]['filename']}")
		return "Bad checksum"
	if os.path.exists(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}"):
		print("Removing old version")
		os.remove(f"{commons.instance_dir}/{commons.instancecfg["modfolder"]}/{index['filename']}")

def parse_api(api_data):
	if api_data["project_type"] == "modpack":
		print(f"{api_data["slug"]} is a modpack")
		logger.error("mcmodman does not currently support modpacks, skipping")
		return "Modpack"

	if api_data["project_type"] == "mod":
		if commons.instancecfg["loader"] in api_data["loaders"]:
			mod_loader = commons.instancecfg["loader"]
		elif "datapack" in api_data["loaders"]:
			logger.error("mcmodman does not currently support datapacks, skipping")
			return "Unsupported project type"
	else:
		logger.error(f"mcmodman does not currently support projects of type '{api_data["project_type"]}', skipping")
		return "Unsupported project type"

	if commons.config["include-beta"]:
		allowed_version_types = ["release", "beta", "alpha"]
	else:
		allowed_version_types = ["release"]
	matches = []
	for version in api_data["versions"]:
		if version["version_type"] in allowed_version_types and commons.minecraft_version in version["game_versions"] and mod_loader in version["loaders"]:
			matches.append(version)
	if not matches:
		print("No matching versions found")
		return "No version"
	return matches


def get_api(slug):
	if os.path.exists(f"{commons.cache_dir}/modrinth-api/{slug}.mm.toml"):
		cache_data = toml.load(f"{commons.cache_dir}/modrinth-api/{slug}.mm.toml")
		if time() - cache_data["time"] < commons.config["api-expire"] and cache_data["api-cache-version"] == 2:
			print(f"Using cached api data for mod '{slug}'")
			mod_data = cache_data["mod-api"]
			logger.info(f"Found cached api data for mod '{slug}' at {commons.cache_dir}/modrinth-api/{slug}.mm.toml")
		else:
			del cache_data
	if "cache_data" not in locals():
		logger.info(f"Could not find valid cache data for mod '{slug}' fetching api data for mod '{slug}' from modrinth")
		print(f"Fetching api data for mod '{slug}'")
		url = f"https://api.modrinth.com/v2/project/{slug}"
		response = get(url, headers={'User-Agent': 'github: https://https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		if response.status_code != 200:
			print(f"Mod '{slug}' not found")
			raise SystemExit
		mod_data = response.json()
		url = f"https://api.modrinth.com/v2/project/{slug}/version"
		response = get(url, headers={'User-Agent': 'github: https://https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		response.raise_for_status()
		mod_data["versions"] = response.json()

		cache_data = {"time": time(), "api-cache-version": 2, "mod-api": mod_data}
		logger.info(f"Caching api data for mod '{slug}' to {commons.cache_dir}/modrinth-api/{slug}.mm.toml")
		with open(f"{commons.cache_dir}/modrinth-api/{slug}.mm.toml", 'w',  encoding='utf-8') as file:
			print(f"Caching api data for mod '{slug}'")
			toml.dump(cache_data, file)

	return mod_data

logger = logging.getLogger(__name__)
