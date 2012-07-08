#!/usr/bin/python

from distutils.core import setup, Extension
from cgutils.version import VERSION

mod_linux = Extension('linux', sources = ['cgutils/linux.c'])

setup(name = 'cgroup-utils',
      version = VERSION,
      description = 'Utility tools for control groups of Linux',
      long_description =
'''cgroup-utils includes some useful libraries and tools to view status, statistics and configurations of control groups.''',
      scripts = ['bin/cgutil',],
      packages = ['cgutils'],
      ext_package = 'cgutils',
      ext_modules = [mod_linux],
      author = 'peo3',
      author_email = 'peo314159265@gmail.com',
      url = 'https://github.com/peo3/cgroup-utils',
      license = 'GPL',
)
