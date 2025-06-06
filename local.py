from shutil import copyfile, SameFileError
import logging, os, json, yaml, zipfile, tomlkit, commons

TAGS = []

def getMod(slug: str, modData: dict):
	try:
		copyfile(modData["filename"], os.path.join(commons.instance_dir, f"{modData["project_type"]}s", os.path.basename(modData["versions"][0]["files"][0]["filename"])))
	except SameFileError:
		pass

def parseAPI(modData: dict) -> list:
	modData["versions"] = [""]
	modData["versions"][0] = {"slug": os.path.basename(modData["filename"]), "dependencies": [], "files": [{"filename": os.path.basename(modData["filename"]), "size": os.path.getsize(modData["filename"])}], "folder": f"{modData["project_type"]}s"}
	if modData["from"] == "pack.mcmeta":
		modData["versions"][0]["id"] = "Unknown"
		modData["versions"][0]["version_number"] = "Unknown"
	if modData["from"] == "mods.toml":
		modData["versions"][0]["id"] = modData["mods"][0]["version"]
		modData["versions"][0]["version_number"] = modData["mods"][0]["version"]
		modData["versions"][0]["slug"] = modData["mods"][0]["modId"]
	elif modData["from"] == "fabric.mod.json":
		modData["versions"][0]["id"] = modData["version"]
		modData["versions"][0]["version_number"] = modData["version"]
		modData["versions"][0]["slug"] = modData["id"]
	elif modData["from"] == "plugin.yml":
		modData["versions"][0]["id"] = modData["version"]
		modData["versions"][0]["version_number"] = modData["version"]
		modData["versions"][0]["slug"] = modData["name"]

	return modData["versions"]

def getAPI(filename: str) -> dict:
	with zipfile.ZipFile(filename, "r") as mod:
		moddir = mod.namelist()
		if "fabric.mod.json" in moddir:
			with mod.open('fabric.mod.json') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "mod"
			modData["from"] = "fabric.mod.json"
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
