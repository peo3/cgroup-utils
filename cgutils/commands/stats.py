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

from cgutils import cgroup
from cgutils import command

class Command(command.Command):
    NAME = 'stats'
    DEFAULT_SUBSYSTEM = 'cpu'

    parser = command.Command.parser
    parser.add_option('-o', action='store', type='string',
                      dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                      help='Specify a subsystem [cpu]')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups [False]')
    parser.add_option('--json', action='store_true',
                      dest='json', default=False,
                      help='Dump as JSON [False]')

    def run(self, args):
        root_cgroup = cgroup.scan_cgroups(self.options.target_subsystem)

        def collect_configs(_cgroup, store):
            if self.options.debug:
                print(_cgroup)
            if self.options.hide_empty and _cgroup.n_procs == 0:
                pass
            else:
                store[_cgroup.path] = _cgroup.get_stats()

        cgroups = {}
        cgroup.walk_cgroups(root_cgroup, collect_configs, cgroups)

        if self.options.json:
            import json
            json.dump(cgroups, sys.stdout, indent=4)
        else:
            for cgname, stats in cgroups.iteritems():
                print(cgname)
                for name, val in stats.iteritems():
                    print("\t%s=%s"%(name, str(val)))

