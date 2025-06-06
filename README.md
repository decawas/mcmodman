# mcmodman

## mcmodman is a cli minecraft instance management utility inspired by and functionally similar to the [arch linux package manager "pacman"](https://wiki.archlinux.org/title/Pacman)

## Usage

1. **Add Mods**:
   ```
   mcmodman -S mod1 mod2 mod3 ...
   ```
   Adds one or more mods to your instance. Replace `mod#` with the desired mod's slug.

2. **Update Mods**:
   ```
   mcmodman -U mod1 mod2 mod3 ...
   ```
   This updates existing mods to their latest versions.
   has an optional "a" flag (-Ua) for updating all installed mods

3. **Remove Mods**:
   ```
   mcmodman -R mod1 mod2 mod3 ...
   ```
   Removes one or more mods from your instance

4. **Query Installed Mods**:
   ```
   mcmodman -Q mod1 mod2 mod3 ...
   ```
   Displays if a mod is installed and which version is installed

5. **Toggle Mod Status**:
   ```
   mcmodman -T mod1 mod2 mod3 ...
   ```
   Enables or disables specific mods.

6. **Search Mod**:
   ```
   mcmodman -F search query
   ```
   Searches on modrinth.

7. **Downgrade Mod**:
   ```
   mcmodman -D mod1 mod2 mod3 ...
   ```
   Allows downloading a specific version of a mod.

6. **Clear Cache**:
   ```
   mcmodman -cc api|content
   ```
   Clears the API or content cache, or both.

7. **Instance Management**:
   ```
   mcmodman --instance add|select|remove
   ```
   Manages instances of the mod manager.

8. **Version Check**:
   ```
   mcmodman --version
   ```
   Displays the current version of the mod manager.

## Build
simply run 
```
python setup.py build
```
requires python and cxfreeze to be installed, the 'appdirs', 'requests', 'tomlkit' and 'pyyaml' modules are dependencies

## Installation

To install mcmodman there are two methods

1. **Copy to /usr/local/bin**

   Link the `mcmodman` executable to the `/usr/local/bin` directory:

   ```bash
   sudo ln -s /path/to/mcmodman /usr/local/bin
   ```
   make sure to replace "/path/to" with the path to your executable

   This method places the executable in a standard location for user-installed programs.

2. **Add to PATH**

   Add mcmodman's directory to PATH:

   ```bash
   echo 'export PATH=$PATH:/path/to/mcmodman/directory' >> ~/.bashrc
   source ~/.bashrc
   ```

   Replace `/path/to/mcmodman/directory` with the actual path where you've placed the `mcmodman` executable.

These methods are for unix-like systems, if you use windows i dont know what you should do im sorry
