#!/usr/bin/python

from setuptools import setup, Extension
from cgutils.version import VERSION

mod_linux = Extension('linux', sources=['cgutils/linux.c'])

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: C',
    'Programming Language :: Python',
    'Topic :: System :: Operating System Kernels :: Linux',
    'Topic :: System :: Systems Administration',
    'Topic :: Utilities',
]

long_description = open('README').read() + '\n' + open('Changelog').read()

setup(name='cgroup-utils',
      version=VERSION,
      description='Utility tools for control groups of Linux',
      long_description=long_description,
      scripts=['bin/cgutil'],
      packages=['cgutils', 'cgutils.commands'],
      ext_package='cgutils',
      ext_modules=[mod_linux],
      author='peo3',
      author_email='peo314159265@gmail.com',
      url='https://github.com/peo3/cgroup-utils',
      license='GPLv2',
      classifiers=classifiers,
      tests_require=['nose', 'pep8'],
      test_suite='nose.collector',
      extras_require=dict(
          test=[
              'nose',
              'pep8',
          ]
      ),)
