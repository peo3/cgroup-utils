#!/usr/bin/python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# See the COPYING file for license information.
#
# Copyright (c) 2012 peo3 <peo314159265@gmail.com>

import sys
import os, os.path
import subprocess
import re
import itertools
import optparse
import glob

parser = optparse.OptionParser()
parser.add_option('--debug', action='store_true', dest='debug',
                  default=False, help='Show debug messages [False]')

options, args = parser.parse_args()

if not os.path.exists('./build/'):
    print('Make sure you already did "python setup.py build"')
    sys.exit(0)

path = glob.glob("./build/lib.linux*")[0]
sys.path.insert(0, '.')
sys.path.insert(0, path)

os.environ['PYTHONPATH'] = "%s:." % path

import cgutils.commands
import cgutils.cgroup as cgroup

def parse_help(output):
    _options = []
    p = re.compile("^  (-\w), --\w+")
    for line in output.split('\n'):
        m = p.search(line)
        if m:
            _options.append(m.group(1))
    _options = [o for o in _options if o != '-h']
    return _options

def execute(cmdline):
    return subprocess.check_output(cmdline.split(' '),
                                   stderr=subprocess.STDOUT,
                                   )

error_outputs = []

def test(cmdline, opts):
    ok = True
    _cmdline = cmdline % ' '.join(opts)
    if options.debug:
        print(_cmdline)
    try:
        execute(_cmdline)
    except subprocess.CalledProcessError as e:
        #print('')
        #print(e)
        error_outputs.append(str(e))
        sys.stdout.write('X')
        sys.stdout.flush()
        ok = False
    else:
        sys.stdout.write('.')
        sys.stdout.flush()
    return ok

def test_subsystem(cmd, cmdline, _options, subsys=None):
    allok = True
    for n in range(len(_options)):
        for opts in itertools.combinations(_options, n + 1):
            opts = list(opts)
            if cmd == 'top':
                opts.extend(['-b', '-n', '3', '-d', '0.1'])
            elif cmd == 'pgrep':
                opts.append('sh')
            elif cmd == 'tree' and '-a' in opts and subsys != 'cpu':
                # In the case, tree always fails
                continue
            if options.debug:
                print(opts)
            allok &= test(cmdline, opts)
    return allok

commands = cgutils.commands.__all__
# FIXME: there is no way to test automatically these commands ;-/
commands = [c for c in commands if c not in ['event', 'mkdir', 'rmdir']]

status = cgroup.SubsystemStatus()
subsystems = status.get_enabled()
subsystems = [s for s in subsystems if s != 'debug' and s != 'perf_event' and 'name=' not in s]

for cmd in commands:
    print("#### Testing %s" % cmd)
    cmdline = '/usr/bin/python ./bin/cgutil %s %%s' % cmd
    output = execute(cmdline % '--help')
    _options = parse_help(output)
    if options.debug:
        print(output)
        print(cmd, _options)
    if not _options:
        _options = ['']

    if cmd in ['configs', 'stats', 'tree']:
        for subsys in subsystems:
            print "%s " % subsys,
            _cmdline = cmdline + " -o %s" % subsys
            allok = test_subsystem(cmd, _cmdline, _options, subsys)
            if allok:
                print('[ok]')
            else:
                print('[NG]')
    else:
        allok = test_subsystem(cmd, cmdline, _options)
        if allok:
            print('[ok]')
        else:
            print('[NG]')
    print('')

for err in error_outputs:
    print(err)
