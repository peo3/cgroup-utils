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
# Copyright (c) 2011-2013 peo3 <peo314159265@gmail.com>

import sys

from cgutils import cgroup
from cgutils import command
from cgutils import formatter
from cgutils import host


class Command(command.Command):
    NAME = 'configs'
    DEFAULT_SUBSYSTEM = 'cpu'
    HELP = 'Show values of configurable cgroup files'

    @staticmethod
    def add_subparser(subparsers):
        parser = subparsers.add_parser(Command.NAME, help=Command.HELP)
        parser.add_argument('-o', dest='target_subsystem',
                            default=Command.DEFAULT_SUBSYSTEM,
                            help='Specify a subsystem [%(default)s]')
        parser.add_argument('-d', '--show-default', action='store_true',
                            help='Show every parameters including default values')
        parser.add_argument('-r', '--show-rate', action='store_true',
                            help='Show rate value to default/current values')
        parser.add_argument('-e', '--hide-empty', action='store_true',
                            help='Hide empty groups')
        parser.add_argument('-j', '--json', action='store_true',
                            help='Dump as JSON')

    def calc_memory_rate(val):
        meminfo = host.MemInfo()
        meminfo.update()
        return float(val) / meminfo['MemTotal']

    _support_rate = {
        'limit_in_bytes': calc_memory_rate,
        'soft_limit_in_bytes': calc_memory_rate,
        'memsw.limit_in_bytes': calc_memory_rate,
        'kmem.tcp.limit_in_bytes': calc_memory_rate,
        'swappiness': None,
        'shares': None,
        'weight': None,
    }

    def _print_configs(self, configs, defaults):
        for name, val in configs.items():
            if 'in_bytes' in name:
                if val == defaults[name]:
                    valstr = ''
                else:
                    valstr = formatter.byte(val)
            else:
                valstr = str(val)
            if self.args.show_rate and name in self._support_rate:
                if self._support_rate[name]:
                    rate = self._support_rate[name](val)
                else:
                    rate = float(val) / defaults[name]
                ratestr = ' (%s)' % formatter.percent(rate)
            else:
                ratestr = ''

            print("\t%s=%s%s" % (name, valstr, ratestr))

    def _collect_changed_configs(self, _cgroup):
        configs = _cgroup.get_configs()
        defaults = _cgroup.get_default_configs()

        ret = {}
        for name, val in configs.items():
            if defaults[name] != val:
                ret[name] = val
        return ret

    def run(self):
        root_cgroup = cgroup.scan_cgroups(self.args.target_subsystem)

        def collect_configs(_cgroup, store):
            if self.args.debug:
                print(_cgroup)

            if self.args.hide_empty and _cgroup.n_procs == 0:
                return
            if self.args.show_default:
                if self.args.json:
                    store[_cgroup.path] = _cgroup.get_configs()
                else:
                    # To calculate rates, default values are required
                    store[_cgroup.path] = (_cgroup.get_configs(), _cgroup.get_default_configs())
                return
            configs = self._collect_changed_configs(_cgroup)
            if configs:
                if self.args.json:
                    store[_cgroup.path] = configs
                else:
                    # To calculate rates, default values are required
                    store[_cgroup.path] = (configs, _cgroup.get_default_configs())

        cgroups = {}
        cgroup.walk_cgroups(root_cgroup, collect_configs, cgroups)
        if self.args.json:
            import json
            json.dump(cgroups, sys.stdout, indent=4)
        else:
            for name, (configs, defaults) in cgroups.items():
                print(name)
                self._print_configs(configs, defaults)
