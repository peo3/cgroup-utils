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
# Copyright (c) 2012,2013 peo3 <peo314159265@gmail.com>
import sys

from cgutils import cgroup
from cgutils import command

if sys.version_info.major == 3:
    long = int


class Command(command.Command):
    NAME = 'stats'
    HELP = 'Show stats of cgroups'
    DEFAULT_SUBSYSTEM = 'cpu'

    @staticmethod
    def add_subparser(subparsers):
        parser = subparsers.add_parser(Command.NAME, help=Command.HELP)
        parser.add_argument('-o', action='store',
                            dest='target_subsystem', default=Command.DEFAULT_SUBSYSTEM,
                            help='Specify a subsystem [%(default)s]')
        parser.add_argument('-e', '--hide-empty', action='store_true',
                            help='Hide empty groups')
        parser.add_argument('-z', '--show-zero', action='store_true',
                            help='Show zero values')
        parser.add_argument('-j', '--json', action='store_true',
                            help='Dump as JSON')

    _INDENT = ' ' * 4

    def _print_stats(self, cgname, stats):
        def print_recursive(name, value, indent):
            if isinstance(value, long):
                if self.args.show_zero or value != 0:
                    return "%s%s=%d\n" % (self._INDENT * indent, name, value)
            elif isinstance(value, list):
                if self.args.show_zero or value:
                    values = [str(v) for v in value]
                    return "%s%s=%s\n" % (self._INDENT * indent,
                                          name,
                                          ', '.join(values))
            elif isinstance(value, dict):
                ret = ''
                for n, v in value.items():
                    ret += print_recursive(n, v, indent + 1)
                if ret:
                    return "%s%s:\n" % (self._INDENT * indent, name) + ret
            return ''

        ret = print_recursive(cgname, stats, 0)
        if ret:
            # XXX python3: print(ret, end=' ') doesn't work on python2
            sys.stdout.write(ret)

    def run(self):
        root_cgroup = cgroup.scan_cgroups(self.args.target_subsystem)

        def collect_configs(_cgroup, store):
            if self.args.debug:
                print(_cgroup)
            if self.args.hide_empty and _cgroup.n_procs == 0:
                pass
            else:
                store[_cgroup.path] = _cgroup.get_stats()

        cgroups = {}
        cgroup.walk_cgroups(root_cgroup, collect_configs, cgroups)

        if self.args.json:
            import json
            json.dump(cgroups, sys.stdout, indent=4)
        else:
            for cgname, stats in cgroups.items():
                self._print_stats(cgname, stats)
