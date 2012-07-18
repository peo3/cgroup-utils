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
from cgutils import host

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

def print_configs(_cgroup, options):
    configs = _cgroup.get_configs()
    defaults = _cgroup.get_default_configs()
    cg_shown = False
    for name, val in configs.iteritems():
        if not options.show_default and defaults[name] == val:
            continue
        if 'in_bytes' in name:
            if val == defaults[name]:
                valstr = ''
            else:
                valstr = formatter.byte2str(val)
        else:
            valstr = str(val)
        if options.show_rate and name in _support_rate:
            if _support_rate[name]:
                rate = _support_rate[name](val)
            else:
                rate = float(val) / defaults[name]
            ratestr = ' (%s)' % formatter.percent2str(rate)
        else:
            ratestr = ''

        if not cg_shown:
            # Want to show only when at least one of configs is changed
            print(_cgroup.fullname)
            cg_shown = True
        print("\t%s=%s%s" % (name, valstr, ratestr))

def run(args, options):
    root_cgroup = cgroup.scan_cgroups(options.target_subsystem)

    def print_cgroups_recursively(_cgroup):
        if options.debug:
            print(_cgroup)

        if options.hide_empty and _cgroup.n_procs == 0:
            pass
        else:
            print_configs(_cgroup, options)
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
parser.add_option('--show-rate', action='store_true',
                  dest='show_rate', default=False,
                  help='Show rate value to default/current values [False]')
parser.add_option('-e', '--hide-empty', action='store_true',
                  dest='hide_empty', default=False,
                  help='Hide empty groups [False]')

