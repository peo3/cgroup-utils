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
                      help='Specify a subsystem [%default]')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups')
    parser.add_option('-z', '--show-zero', action='store_true',
                      dest='show_zero', default=False,
                      help='Show zero values')
    parser.add_option('-j', '--json', action='store_true',
                      dest='json', default=False,
                      help='Dump as JSON')
    parser.usage = "%%prog %s [options]" % NAME

    _INDENT = ' ' * 4

    def _print_stats(self, cgname, stats):
        def print_recursive(name, value, indent):
            if isinstance(value, long):
                if self.options.show_zero or value != 0:
                    return "%s%s=%d\n" % (self._INDENT * indent, name, value)
            elif isinstance(value, list):
                if self.options.show_zero or value:
                    values = [str(v) for v in value]
                    return "%s%s=%s\n" % (self._INDENT * indent,
                                          name,
                                          ', '.join(values))
            elif isinstance(value, dict):
                ret = ''
                for n, v in value.iteritems():
                    ret += print_recursive(n, v, indent + 1)
                if ret:
                    return "%s%s:\n" % (self._INDENT * indent, name) + ret
            return ''

        ret = print_recursive(cgname, stats, 0)
        if ret:
            print ret,

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
                self._print_stats(cgname, stats)
