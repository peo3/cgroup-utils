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
# Copyright (c) 2011,2012 peo3 <peo314159265@gmail.com>

from __future__ import with_statement
import sys
import os, os.path
import optparse

from cgutils import cgroup
from cgutils import process
from cgutils import formatter
from cgutils.version import VERSION

def run(args, options):
    root_cgroup = cgroup.scan_cgroups(options.target_subsystem)
    procname = args[0]

    def print_matched(_cg, dummy):
        _cg.update_pids()
        procs = []
        for pid in _cg.pids:
            proc = process.Process(pid)
            if options.full_args:
                comp = proc.cmdline
            else:
                comp = proc.name
            if procname in comp:
                if options.show_name:
                    if options.full_args:
                        output = "%d %s" % (proc.pid, proc.cmdline)
                    else:
                        output = "%d %s" % (proc.pid, proc.name)
                else:
                    output = str(proc.pid)
                print('%s: %s'%(_cg.path, output))

    cgroup.walk_cgroups(root_cgroup, print_matched, None)

DEFAULT_SUBSYSTEM = 'cpu'

parser = optparse.OptionParser(version='cgshowconfigs '+VERSION)
parser.add_option('-o', action='store', type='string',
                  dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                  help='Specify a subsystem [cpu]')
parser.add_option('-f', '--full-args', action='store_true',
                  dest='full_args', default=False,
                  help='Show all arguments of processes [False]')
parser.add_option('-l', '--name', action='store_true',
                  dest='show_name', default=False,
                  help='Show name of processes [False]')
