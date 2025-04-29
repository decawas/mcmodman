from shutil import copyfile
import logging, os, json, yaml, zipfile, toml, commons

def getMod(slug, modData, index):
	copyfile(modData["filename"], os.path.join(commons.instance_dir, f"{modData["project_type"]}s", os.path.basename(modData["versions"][0]["files"][0]["filename"])))

def parseAPI(modData):
	modData["versions"] = [""]
	modData["versions"][0] = {"slug": os.path.basename(modData["filename"]), "dependencies": [], "files": [{"filename": os.path.basename(modData["filename"]), "size": os.path.getsize(modData["filename"])}], "folder": f"{modData["project_type"]}s"}
	if modData.get("type") in ["shaderpack", "datapack", "resourcepack"]:
		modData["versions"][0]["id"] = "Unknown"
		modData["versions"][0]["version_number"] = "Unknown"
	if modData.get("modLoader") == "javafml":
		modData["versions"][0]["id"] = modData["mods"][0]["version"]
		modData["versions"][0]["version_number"] = modData["mods"][0]["version"]
		modData["versions"][0]["slug"] = modData["mods"][0]["modId"]
	elif modData.get("main") is None:
		modData["versions"][0]["id"] = modData["version"]
		modData["versions"][0]["version_number"] = modData["version"]
		modData["versions"][0]["slug"] = modData["id"]
	elif modData.get("main") is not None:
		modData["versions"][0]["id"] = modData["version"]
		modData["versions"][0]["version_number"] = modData["version"]
		modData["versions"][0]["slug"] = modData["name"]
	
	return modData["versions"]

def getAPI(filename):
	with zipfile.ZipFile(filename, "r") as mod:
		moddir = mod.namelist()
		if "fabric.mod.json" in moddir:
			with mod.open('fabric.mod.json') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "mod"
		elif "META-INF/mods.toml" in moddir:
			with mod.open('META-INF/mods.toml') as data:
				modData = toml.loads(data.read().decode("utf-8"))
			modData["project_type"] = "mod"
		elif "plugin.yml" in moddir:
			with mod.open('plugin.yml') as data:
				modData = yaml.load(data.read().decode("utf-8"), yaml.CSafeLoader)
			modData["project_type"] = "plugin"
		elif "assets/" in moddir and "pack.mcmeta" in moddir:
			with mod.open('pack.mcmeta') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "resourcepack"
		elif "data/" in moddir and "pack.mcmeta" in moddir:
			with mod.open('pack.mcmeta') as data:
				modData = json.loads(data.read().decode("utf-8"))
			modData["project_type"] = "datapack"
		elif "shaders/" in moddir:
			modData = {"project_type": "shaderpack"}
		else:
			print("unknown mod format")
			raise Exception
	
	modData["id"] = os.path.basename(filename)
	modData["filename"] = filename
	return modData
