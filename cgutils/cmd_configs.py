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

import sys
import optparse

from cgutils import cgroup
from cgutils import formatter
from cgutils.version import VERSION

def print_configs(_cgroup, show_default):
    configs = _cgroup.get_configs()
    defaults = _cgroup.get_default_configs()
    for name, val in configs.iteritems():
        if not show_default and defaults[name] == val:
            continue
        if 'in_bytes' in name:
            if val == defaults[name]:
                print("\t%s="%(name,))
            else:
                print("\t%s=%s"%(name, formatter.byte2str(val)))
        else:
            print("\t%s=%s"%(name, str(val)))

def run(args, options):
    root_cgroup = cgroup.scan_cgroups(options.target_subsystem)

    def print_cgroups_recursively(_cgroup):
        if options.debug:
            print(_cgroup)

        if options.hide_empty and _cgroup.n_procs == 0:
            pass
        else:
            print(_cgroup.fullname)
            print_configs(_cgroup, options.show_default)
        for child in _cgroup.childs:
            print_cgroups_recursively(child)
    print_cgroups_recursively(root_cgroup)

DEFAULT_SUBSYSTEM = 'cpu'

parser = optparse.OptionParser(version='cgshowconfigs '+VERSION)
parser.add_option('-o', action='store', type='string',
                  dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                  help='Specify a subsystem [cpu]')
parser.add_option('--show-default', action='store_true',
                  dest='show_default', default=False,
                  help='Show every parameters including default values [False]')
parser.add_option('-e', '--hide-empty', action='store_true',
                  dest='hide_empty', default=False,
                  help='Hide empty groups [False]')

