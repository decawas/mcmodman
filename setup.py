from cx_Freeze import setup, Executable
import sys

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {
    'packages': [],
    'excludes': [],
    'include_files': [('dataversion.json', 'dataversion.json'), ('config-template.ini', 'config-template.ini')],
    'optimize': 2,
}

base = 'console'

executables = [Executable('mcmodman.py', base=base,)]

setup(name='mcmodman',
      version = '25.22',
      description = 'yet another minecraft mod manager',
      options = {'build_exe': build_options},
      executables = executables)
