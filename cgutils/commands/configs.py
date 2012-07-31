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

from cgutils import cgroup
from cgutils import command
from cgutils import formatter
from cgutils import host


class Command(command.Command):
    NAME = 'configs'
    DEFAULT_SUBSYSTEM = 'cpu'

    parser = command.Command.parser
    parser.add_option('-o', action='store', type='string',
                      dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                      help='Specify a subsystem [%default]')
    parser.add_option('-d', '--show-default', action='store_true',
                      dest='show_default', default=False,
                      help='Show every parameters including default values')
    parser.add_option('-r', '--show-rate', action='store_true',
                      dest='show_rate', default=False,
                      help='Show rate value to default/current values')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups')
    parser.add_option('-j', '--json', action='store_true',
                      dest='json', default=False,
                      help='Dump as JSON')
    parser.usage = "%%prog %s [options]" % NAME

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
        for name, val in configs.iteritems():
            if 'in_bytes' in name:
                if val == defaults[name]:
                    valstr = ''
                else:
                    valstr = formatter.byte(val)
            else:
                valstr = str(val)
            if self.options.show_rate and name in self._support_rate:
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
        for name, val in configs.iteritems():
            if defaults[name] != val:
                ret[name] = val
        return ret

    def run(self, args):
        root_cgroup = cgroup.scan_cgroups(self.options.target_subsystem)

        def collect_configs(_cgroup, store):
            if self.options.debug:
                print(_cgroup)

            if self.options.hide_empty and _cgroup.n_procs == 0:
                return
            if self.options.show_default:
                if self.options.json:
                    store[_cgroup.path] = _cgroup.get_configs()
                else:
                    # To calculate rates, default values are required
                    store[_cgroup.path] = (_cgroup.get_configs(), _cgroup.get_default_configs())
                return
            configs = self._collect_changed_configs(_cgroup)
            if configs:
                if self.options.json:
                    store[_cgroup.path] = configs
                else:
                    # To calculate rates, default values are required
                    store[_cgroup.path] = (configs, _cgroup.get_default_configs())

        cgroups = {}
        cgroup.walk_cgroups(root_cgroup, collect_configs, cgroups)
        if self.options.json:
            import json
            json.dump(cgroups, sys.stdout, indent=4)
        else:
            for name, (configs, defaults) in cgroups.iteritems():
                print(name)
                self._print_configs(configs, defaults)
