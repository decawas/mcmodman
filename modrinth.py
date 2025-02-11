# pylint: disable=C0114 C0116 C0410 C0411 E0606
from hashlib import sha512
from time import time
from shutil import copyfile
import logging, os, toml, commons
from requests import get

def get_mod(slug, mod_data, index):
	if os.path.exists(os.path.join(commons.cache_dir, "mods", f"{mod_data['versions'][0]['files'][0]['filename']}.mm.toml")):
		print(f"Using cached version for mod '{slug}'")
		copyfile(os.path.join(commons.cache_dir, "mods", mod_data['versions'][0]['files'][0]['filename']), os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod_data["versions"][0]['files'][0]['filename']))
		copyfile(os.path.join(commons.cache_dir, "mods", f"{mod_data['versions'][0]['files'][0]['filename']}.mm.toml"), os.path.join(commons.instance_dir, ".content", f"{slug}.mm.toml"))
		return
	else:
		print(f"Downloading mod '{slug}'")
		url = f"{mod_data['versions'][0]['files'][0]['url']}"
		response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		logger.info('Modrinth returned headers %s', response.headers)
		if response.status_code != 200:
			logger.error('Modrinth download returned %s', response.status_code)
			return

	_, folder = project_get_type(mod_data)

	if folder == "":
		with open("server.properties", "r", encoding="utf-8") as f:
			properties = toml.loads(f.read())
		folder = os.path.join(properties["level-name"], "datapacks")

	with open(os.path.join(commons.instance_dir, folder, mod_data['versions'][0]["files"][0]["filename"]), "wb") as f:
		f.write(response.content)

	if commons.config["checksum"] in ["Always", "Download"] and not os.path.exists(os.path.join(commons.cache_dir, commons.instancecfg["modfolder"], f"{mod_data['versions'][0]['files'][0]['filename']}.mmcache.toml")):
		perfcheck = True
	elif commons.config["checksum"] == "Always":
		perfcheck = True
	elif commons.config["checksum"] == "Never":
		perfcheck = False
	else:
		perfcheck = True

	if perfcheck:
		print("Checking hash")
		with open(os.path.join(commons.instance_dir, folder, mod_data["versions"][0]['files'][0]['filename']), 'rb') as f:
			checksum = sha512(f.read()).hexdigest()
		if mod_data["versions"][0]["files"][0]["hashes"]["sha512"] != checksum:
			print("Failed to validate file")
			os.remove(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], mod_data['files'][0]['filename']))
		return
	if os.path.exists(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], {index['filename']})):
		print("Removing old version")
		os.remove(os.path.join(commons.instance_dir, commons.instancecfg["modfolder"], {index['filename']}))

def parse_api(api_data):
	ptype, _ = project_get_type(api_data)
	if ptype == "modpack":
		print(f"{api_data['slug']} is a modpack")
		logger.error("mcmodman does not currently support modpacks, skipping")
		return "Modpack"

	if ptype == "mod":
		mod_loader = commons.instancecfg["loader"]
	elif ptype in ["shader", "resourcepack"]:
		if os.path.exists(os.path.join(commons.instance_dir, "server.properties")):
			print(f"{ptype}s do not work on servers, skipping")
			logger.warning("content of type '%s' can not be used on servers", ptype)
			return ptype
		mod_loader = api_data["loaders"][0]
	elif ptype == "datapack":
		if not os.path.exists("server.properties"):
			print("mcmodman does not currently support datapacks for clients, skipping")
			logger.warning("content of type '%s' can not be used on clients", ptype)
			return ptype
		mod_loader = "datapack"

	matches = {"release": [], "beta": [], "alpha": []}
	for version in api_data["versions"]:
		if commons.minecraft_version in version["game_versions"] and mod_loader in version["loaders"]:
			matches[version["version_type"]].append(version)
	if not matches:
		print(f"No matching versions found for mod '{api_data['slug']}'")
		logger.error("No matching versions found for mod '%s", api_data['slug'])
		return "No version"
	matches = matches["release"].append(matches["beta"]).append(matches["alpha"])
	return matches


def get_api(slug):
	if os.path.exists(os.path.join(commons.cache_dir, "modrinth-api", f"{slug}.mmcache.toml")):
		cache_data = toml.load(os.path.join(commons.cache_dir, "modrinth-api", f"{slug}.mmcache.toml"))
		if time() - cache_data["time"] < commons.config["api-expire"] and cache_data["api-cache-version"] == 2:
			print(f"Using cached api data for mod '{slug}'")
			mod_data = cache_data["mod-api"]
			logger.info("Found cached api data for mod %s at %s", slug, commons.cache_dir + '/modrinth-api/' + slug + '.mmcache.toml')
		else:
			del cache_data

	if "cache_data" not in locals():
		logger.info("Could not find valid cache data for mod %s fetching api data for mod %s from modrinth", slug, slug)
		print(f"Fetching api data for mod '{slug}'")
		url = f"https://api.modrinth.com/v2/project/{slug}"
		response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		if response.status_code != 200:
			print(f"Mod '{slug}' not found")
			raise SystemExit
		mod_data = response.json()
		url = f"https://api.modrinth.com/v2/project/{slug}/version"
		response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		response.raise_for_status()
		mod_data["versions"] = response.json()

		cache_data = {"time": time(), "api-cache-version": 2, "mod-api": mod_data}
		logger.info("Caching api data for mod %s to %s", slug, commons.cache_dir + '/modrinth-api/' + slug + '.mmcache.toml')
		with open(os.path.join(commons.cache_dir, "modrinth-api", f"{slug}.mmcache.toml"), 'w',  encoding='utf-8') as file:
			print(f"Caching api data for mod '{mod_data['slug']}'")
			toml.dump(cache_data, file)
		if slug != mod_data['slug']:
			with open(os.path.join(commons.cache_dir, "modrinth-api", f"{mod_data['slug']}.mmcache.toml"), 'w',  encoding='utf-8') as file:
				toml.dump(cache_data, file)


	return mod_data

def search_api(query):
	if os.path.exists(os.path.join(commons.cache_dir, "modrinth-api", f"{query}.modrinthquery.toml")):
		cache_data = toml.load(os.path.join(commons.cache_dir, "modrinth-api", f"{query}.modrinthquery.toml"))
		if time() - cache_data["time"] < commons.config["api-expire"] and cache_data["query-cache-version"] == 0:
			print(f"Using cached query data for mod query '{query}'")
			query_data = cache_data["query-api"]
			logger.info("Found cached query data for mod query '%s' at %s", query, f"{commons.cache_dir}/modrinth-api/{query}.modrinthquery.toml")
		else:
			del cache_data

	if "cache_data" not in locals():
		logger.info("Could not find valid cache data for query '%s'", query)
		print(f"Querying modrinth with query '{query}'")
		url = f"https://api.modrinth.com/v2/search?limit=48&index=downloads&query={query.replace(' ', '+')}&facets=[[\"project_types!=modpack\"],[\"versions:{commons.minecraft_version}\"],[\"categories:{commons.mod_loader}\"]]"
		response = get(url, headers={'User-Agent': 'github: https://github.com/decawas/mcmodman discord: .ekno'}, timeout=30)
		response.raise_for_status()
		query_data = response.json()

		cache_data = {"time": time(), "query-cache-version": 0, "query-api": query_data}
		logger.info("Caching data for query '%s' to %s", query, f"{commons.cache_dir}/modrinth-api/{query}.modrinthquery.toml")
		with open(os.path.join(commons.cache_dir, "modrinth-api", f"{query}.modrinthquery.toml"), 'w',  encoding='utf-8') as file:
			print(f"Caching data for query '{query}'")
			toml.dump(cache_data, file)

	return query_data

def project_get_type(api_data):
	if api_data["project_type"] == "modpack":
		ptype = "modpack"
		folder = ""
	elif api_data["project_type"] in ["shader", "resourcepack"]:
		ptype = api_data["project_type"]
		folder = os.path.join(commons.instance_dir, "shaderpacks" if api_data["project_type"] == "shader" else "resourcepacks")
	elif api_data["project_type"] == "mod":
		if commons.instancecfg["loader"] in api_data["loaders"]:
			ptype = "mod"
			folder = os.path.join(commons.instance_dir, commons.instancecfg["modfolder"])
		elif "datapack" in api_data["loaders"]:
			ptype = "datapack"
			folder = os.path.join("world" if os.path.exists("server.properties") else "", "datapacks")
		else:
			raise ValueError
	else:
		raise ValueError

	return ptype, folder

logger = logging.getLogger(__name__)
