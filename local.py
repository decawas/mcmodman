from shutil import copyfile, SameFileError
import logging, os, json, yaml, zipfile, tomlkit

TAGS = []

def getMod(ctx, slug: str, modData: dict):
	try:
		copyfile(modData["filename"], os.path.join(ctx.instanceDir, f"{modData["project_type"]}s", os.path.basename(modData["versions"][0]["files"][0]["filename"])))
	except SameFileError:
		pass

def parseAPI(ctx, apiData: dict) -> list:
	apiData["versions"] = [""]
	apiData["versions"][0] = {"dependencies": [], "files": [{"filename": os.path.basename(apiData["filename"]), "size": os.path.getsize(apiData["filename"])}], "folder": f"{apiData["project_type"]}s"}
	if apiData["from"] == "pack.mcmeta":
		apiData["versions"][0]["id"] = "Unknown"
		apiData["versions"][0]["version_number"] = "Unknown"
	if apiData["from"] == "mods.toml":
		apiData["versions"][0]["id"] = apiData["mods"][0]["version"]
		apiData["versions"][0]["version_number"] = apiData["mods"][0]["version"]
		apiData["versions"][0]["slug"] = apiData["mods"][0]["modId"]
	elif apiData["from"] == "fabric.mod.json":
		apiData["versions"][0]["id"] = apiData["version"]
		apiData["versions"][0]["version_number"] = apiData["version"]
		apiData["versions"][0]["slug"] = apiData["slug"]
	elif apiData["from"] == "plugin.yml":
		apiData["versions"][0]["id"] = apiData["version"]
		apiData["versions"][0]["version_number"] = apiData["version"]
		apiData["versions"][0]["slug"] = apiData["name"]
	return apiData["versions"]

def getAPI(ctx, filename: str) -> dict:
	with zipfile.ZipFile(filename, "r") as mod:
		moddir = mod.namelist()
		if "fabric.mod.json" in moddir:
			with mod.open('fabric.mod.json') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "mod"
			modData["from"] = "fabric.mod.json"
			modData["slug"] = modData["id"]
		elif "META-INF/mods.toml" in moddir:
			with mod.open('META-INF/mods.toml') as data:
				modData = tomlkit.loads(data.read().decode("utf-8"))
			modData["project_type"] = "mod"
			modData["from"] = "mods.toml"
		elif "plugin.yml" in moddir:
			with mod.open('plugin.yml') as data:
				modData = yaml.load(data.read().decode("utf-8"), yaml.CSafeLoader)
			modData["project_type"] = "plugin"
			modData["from"] = "plugin.yml"
		elif "assets/" in moddir and "pack.mcmeta" in moddir:
			with mod.open('pack.mcmeta') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "resourcepack"
			modData["from"] = "pack.mcmeta"
		elif "data/" in moddir and "pack.mcmeta" in moddir:
			with mod.open('pack.mcmeta') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "datapack"
			modData["from"] = "pack.mcmeta"
		elif "shaders/" in moddir:
			modData = {"project_type": "shaderpack", "from": "pack.mcmeta"}
		else:
			print("unknown mod format")
			raise ValueError

	modData["id"] = os.path.basename(filename)
	modData["filename"] = filename
	modData["source"] = "local"
	return modData