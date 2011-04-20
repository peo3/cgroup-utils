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
# Copyright (c) 2011 peo3 <peo314159265@gmail.com>

from __future__ import with_statement
import os, os.path
import re

import host

def readfile(filepath):
    with open(filepath) as f:
        return f.read()

#
# Get enabled cgroup subsystems
#
subsystem_names = []
"""
#subsys_name	hierarchy	num_cgroups	enabled
cpuset	0	1	1
ns	0	1	1
cpu	1	10	1
cpuacct	0	1	1
memory	0	1	1
devices	0	1	1
freezer	0	1	1
net_cls	0	1	1
"""
_p = re.compile('^(?P<name>\w+)\s+(?P<hier>\d+)\s+(?P<n>\d+)\s+(?P<enabled>[01])')
lines = readfile('/proc/cgroups').split('\n')
for line in lines:
    m = _p.match(line)
    if m is None: continue

    name = m.group('name')
    hierarchy = int(m.group('hier'))
    n_cgroups = int(m.group('n'))
    if m.group('enabled') == '1':
        enabled = True
    else:
        enabled = False
    subsystem_names.append(name)

#
# Get path of enabled subsystems
#
subsystem2path = {}
"""
cgroup /dev/cgroup/cpu cgroup rw,relatime,cpuacct,cpu,release_agent=/usr/local/sbin/cgroup_clean 0 0
cgroup /dev/cgroup/memory cgroup rw,relatime,memory 0 0
cgroup /dev/cgroup/blkio cgroup rw,relatime,blkio 0 0
cgroup /dev/cgroup/freezer cgroup rw,relatime,freezer 0 0
"""
lines = readfile('/proc/mounts').split('\n')
for line in lines:
    if 'cgroup' not in line: continue

    items = line.split(' ')
    path = items[1]
    opts = items[3].split(',')

    for opt in opts:
        if opt in subsystem_names:
            subsystem2path[opt] = path

#
# Sussystems and Cgroup classes
#
class Subsystem(object):
    def __init__(self, path):
        self.path = path

        self.CONFIGS = self._DEFAULTS.keys()
        self.DEFAULTS = {}
        for name, val in self._DEFAULTS.iteritems():
            self.DEFAULTS[self.NAME+'.'+name] = val

        self.param2path = {}
        for param in self.CONFIGS+self.STATS:
            attrname = 'path_'+param.replace('.', '_').replace('#', '_')
            if '#' in param:
                paramname = param.split('#')[0]
            else:
                paramname = param
            _path = os.path.join(self.path, self.NAME+'.'+paramname)
            setattr(self, attrname, _path)
            self.param2path[paramname] = _path

    def get_configs(self):
        configs = {}
        for config in self.CONFIGS:
            if '#' in config: continue

            val = long(readfile(self.param2path[config]))
            configs[self.NAME+'.'+config] = val
        return configs

    def get_default_configs(self):
        return self.DEFAULTS.copy()

    def get_usages(self):
        usages = {}
        for stat in self.STATS:
            val = long(readfile(self.param2path[stat]))
            usages[self.NAME+'.'+stat] = val
        return usages

class SubsystemCpu(Subsystem):
    NAME = 'cpu'
    STATS = []
    _DEFAULTS = {
        'shares': 1024,
        }

class SubsystemCpuacct(Subsystem):
    NAME = 'cpuacct'
    STATS = [
        'usage',
        'stat',
        ]
    _DEFAULTS = {}

    def get_usages(self):
        usage = int(readfile(self.path_usage))
        user, system = readfile(self.path_stat).split('\n')[:2]
        return {'user': int(user.split(' ')[1]),
                'system': int(system.split(' ')[1]),
                'usage': usage}

class SubsystemCpuset(Subsystem):
    NAME = 'cpuset'
    STATS = [
        'memory_pressure',
    ]
    _DEFAULTS = {
        'cpu_exclusive': 0,
        'cpus': host.CPUInfo().get_online(),
        'mem_exclusive': 0,
        'mem_hardwall': 0,
        'memory_migrate': 0,
        'memory_pressure_enabled': 0,
        'memory_spread_page': 0,
        'memory_spread_slab': 0,
        'mems': host.MemInfo().get_online(),
        'sched_load_balance': 1,
        'sched_relax_domain_level': -1,
    }

    def get_configs(self):
        configs = {}
        for config in self.CONFIGS:
            if config in ['mems', 'cpus']:
                val = readfile(self.param2path[config]).strip()
            else:
                val = long(readfile(self.param2path[config]))
            configs['cpuset.'+config] = val
        return configs

class SubsystemMemory(Subsystem):
    NAME = 'memory'
    STATS = [
        'usage_in_bytes',
        'memsw.usage_in_bytes',
        'stat',
        'memsw.failcnt',
        ]
    MAX_ULONGLONG = 2**63-1
    _DEFAULTS = {
        'limit_in_bytes': MAX_ULONGLONG,
        'memsw.limit_in_bytes': MAX_ULONGLONG,
        'move_charge_at_immigrate': 0,
        'oom_control#oom_kill_disable': 0,
        'oom_control#under_oom': 0,
        'soft_limit_in_bytes': MAX_ULONGLONG,
        'swappiness': 60,
        'use_hierarchy': 0,
        }

    def __init__(self, path):
        Subsystem.__init__(self, path)
        self.meminfo = host.MemInfo()
        self._p = re.compile('rss (?P<val>\d+)')

    def get_rss(self):
        cont = readfile(self.path_stat)
        return long(self._p.search(cont).group('val'))

    def get_usages(self):
        usages = {}
        usages['total'] = long(readfile(self.path_usage_in_bytes))
        usages['swap']  = long(readfile(self.path_memsw_usage_in_bytes)) - usages['total']
        usages['rss']   = self.get_rss()
        return usages

    def get_configs(self):
        configs = Subsystem.get_configs(self)
        lines = readfile(self.param2path['oom_control']).split('\n')
        name, val = lines[0].split(' ')
        configs['memory.oom_control#'+name] = long(val)
        name, val = lines[1].split(' ')
        configs['memory.oom_control#'+name] = long(val)
        return configs

class SubsystemBlkio(Subsystem):
    NAME = 'blkio'
    STATS = [
        'io_service_bytes',
        ]
    _DEFAULTS = {
        'weight': 1000,
        'weight_device': '',
        'throttle.read_iops_device': '',
        'throttle.write_iops_device': '',
        'throttle.read_bps_device': '',
        'throttle.write_bps_device': '',
        }

    def get_usages(self):
        usages = {'read':0, 'write':0}
        for line in readfile(self.path_io_service_bytes).split('\n'):
            try:
                (dev,type,bytes) = line.split(' ')
            except ValueError:
                # The last line consists of two items; we can ignore it.
                break
            if type == 'Read':  usages['read'] += long(bytes)
            if type == 'Write': usages['write'] += long(bytes)
        return usages

    def get_configs(self):
        configs = {}
        for config in self.CONFIGS:
            if '_device' in config:
                cont = readfile(self.param2path[config])
                cont = cont.strip().replace('\n', ', ').replace('\t', ' ')
                configs['blkio.'+config] = cont
            else:
                configs['blkio.'+config] = long(readfile(self.param2path[config]))
        return configs

class SubsystemFreezer(Subsystem):
    NAME = 'freezer'
    STATS = {
        'state',
        }
    _DEFAULT = {}

    def get_usages(self):
        # XXX
        try:
            return {'state': "%s"%(readfile(self.path_state).strip(),),}
        except IOError:
            # Root group does not have the file
            return {'state': ''}

subsystem_name2class = {
    'cpu':SubsystemCpu,
    'cpuacct':SubsystemCpuacct,
    'cpuset':SubsystemCpuset,
    'memory':SubsystemMemory,
    'blkio':SubsystemBlkio,
    'freezer':SubsystemFreezer,
}
subsystem_class2name = {}
for name, _class in subsystem_name2class.iteritems():
    subsystem_class2name[_class] = name

class CGroup(object):
    def calc_depth(self, path):
        def rec(path):
            rest = os.path.split(path)[0]
            if rest == '/': return 1
            else: return rec(rest) + 1
        return rec(path)

    def __init__(self, mount_point, relpath, subsystem):
        self.mount_point = mount_point
        self.relpath = relpath
        self.abspath = os.path.normpath(self.mount_point+relpath)
        if self.relpath == '':
            self.depth = 0
        else:
            self.depth = self.calc_depth(self.relpath)
        self.name = os.path.basename(relpath)
        if self.name == '':
            self.fullname = self.name = '<root>'
        else:
            self.fullname = self.relpath[1:]
        self.path_procs = os.path.join(self.abspath,'cgroup.procs')
        self.subsystem = subsystem

        self.childs = []

        self.__update_usages()
        self._update_n_procs()

        self.path_release_agent = os.path.join(self.abspath, 'release_agent')
        self.path_notify_on_release = os.path.join(self.abspath, 'notify_on_release')


    def update_pids(self):
        pids = readfile(self.path_procs).split('\n')[:-1]
        self.pids = [int(pid) for pid in pids]

    def _update_n_procs(self):
        self.n_procs = readfile(self.path_procs).count("\n") - 1
        if self.n_procs == -1: self.n_procs = 0

    def __update_usages(self):
        self.usages = self.subsystem.get_usages()

    def _update_usages(self):
        prev = self.usages
        self.__update_usages()
        self.usages_delta = {}
        for name, usage in self.usages.iteritems():
            self.usages_delta[name] = usage - prev[name]

    def update(self):
        self._update_n_procs()
        self._update_usages()

    def get_configs(self):
        configs = self.subsystem.get_configs()
        if os.path.exists(self.path_release_agent):
            configs['release_agent'] = readfile(self.path_release_agent).strip()
        configs['notify_on_release'] = int(readfile(self.path_notify_on_release))
        return configs

    def get_default_configs(self):
        configs = self.subsystem.get_default_configs()
        if os.path.exists(self.path_release_agent):
            configs['release_agent'] = ''
        configs['notify_on_release'] = 0
        return configs

    def is_kthread(self, pid):
        #return 'VmStk' not in readfile('/proc/%d/status'%(pid,))
        return len(readfile('/proc/%d/coredump_filter'%(pid,))) == 0

    def get_cmd(self, pid):
        return readfile('/proc/%d/comm'%(pid,))[:-1]

def scan_directory_recursively(subsystem, abspath, mount_point):
    relpath = abspath.replace(mount_point, '')
    cgroup = CGroup(mount_point, relpath,
                    subsystem_name2class[subsystem](abspath))

    _childs = []
    for _file in os.listdir(abspath):
        child_abspath = os.path.join(abspath,_file)
        if os.path.isdir(child_abspath):
            child = scan_directory_recursively(subsystem, child_abspath, mount_point)
            _childs.append(child)
    cgroup.childs.extend(_childs)
    return cgroup

def walk_cgroups(cgroup, action, opaque):
    action(cgroup, opaque)
    for child in cgroup.childs:
        walk_cgroups(child, action, opaque)
