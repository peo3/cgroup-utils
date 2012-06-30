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
import os, os.path
import re

from cgutils import host

def readfile(filepath):
    with open(filepath) as f:
        return f.read()

class SubsystemStatus(dict):
    def __init__(self):
        self.update()

    def _parse_proc_cgroups(self):
        """Parse /proc/cgroups"""

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
        p = re.compile('^(?P<name>\w+)\s+(?P<hier>\d+)\s+(?P<n>\d+)\s+(?P<enabled>[01])')
        lines = readfile('/proc/cgroups').split('\n')
        for line in lines:
            m = p.match(line)
            if m is None: continue

            name = m.group('name')
            hierarchy = int(m.group('hier'))
            n_cgroups = int(m.group('n'))
            if m.group('enabled') == '1':
                enabled = True
            else:
                enabled = False
            if name not in self:
                self[name] = {}
            self[name]['name'] = name
            self[name]['hierarchy'] = hierarchy
            self[name]['num_cgroups'] = n_cgroups
            self[name]['enabled'] = enabled

    def _parse_proc_mount(self):
        """Parse /proc/mounts"""

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
                if opt in self:
                    self.paths[opt] = path

    def _update(self):
        self._parse_proc_cgroups()
        self._parse_proc_mount()

    def update(self):
        self.clear()
        self.paths = {}
        self._update()

    def get_all(self):
        return self.keys()

    def get_available(self):
        return [name for name in self.keys()
                if self[name]['enabled'] ]

    def get_enabled(self):
        return self.paths.keys()

    def get_path(self, subsys):
        return self.paths[subsys]

"""
user 2978976
system 1037760
"""
class SimpleStat(dict):
    @staticmethod
    def parse(path):
        ret = {}
        for line in readfile(path).split('\n')[:-1]:
            name, val = line.split(' ')
            ret[name] = long(val)
        return ret

"""
8:0 Read 72650752
8:0 Write 28090368
8:0 Sync 28090368
8:0 Async 72650752
8:0 Total 100741120
Total 100741120
"""
class BlkioStat(dict):
    @staticmethod
    def parse(path):
        ret = {}
        for line in readfile(path).split('\n')[:-1]:
            if line.count(' ') == 2:
                dev, type, val = line.split(' ')
                if dev not in ret:
                    ret[dev] = {}
                ret[dev][type] = long(val)
            elif line.count(' ') == 1:
                type, val = line.split(' ')
                ret[type] = long(val)
            else:
                raise EnvironmentError(line)
        return ret

"""
a *:* rwm

c 136:* rwm
c 1:3 rwm
c 1:7 rwm
c 1:5 rwm
c 1:8 rwm
c 1:9 rwm
c 5:2 rwm
c 10:232 rwm
c 254:0 rwm
c 10:228 rwm
c 10:200 rwm
c 251:0 rwm
c 251:1 rwm
c 251:2 rwm
c 251:3 rwm
c 251:4 rwm
"""
class DevicesStat(list):
    @staticmethod
    def parse(path):
        return readfile(path).split('\n')[:-1]

"""
total=83920 N0=83920
file=63452 N0=63452
anon=20468 N0=20468
unevictable=0 N0=0
"""
class NumaStat(dict):
    @staticmethod
    def parse(path):
        ret = {}
        lines = readfile(path).split('\n')[:-1]
        for line in lines:
            item = {}
            entries = line.split(' ')
            name, value = entries[0].split('=')
            item['total'] = long(value)
            for entry in entries[1:]:
                node, value = entry.split('=')
                item[node] = long(value)
            ret[name] = item
        return ret

"""
# Two CPUs
836842800783 656015556351 
"""
class PercpuStat(dict):
    @staticmethod
    def parse(path):
        ret = {}
        line = readfile(path).split('\n')[0]
        stats = line.split(' ')
        # A line may end with a redundant space
        stats = [ stat for stat in stats if stat != '' ]
        print stats
        i = 0
        for stat in stats:
            ret[i] = long(stat)
            i += 1
        return ret

#
# The base class of subsystems
#
class Subsystem(object):
    PARSERS = {
        int:  lambda path: int(readfile(path)),
        long: lambda path: long(readfile(path)),
        str:  lambda path: readfile(path).strip(),
        SimpleStat: SimpleStat.parse,
        BlkioStat: BlkioStat.parse,
        DevicesStat: DevicesStat.parse,
        NumaStat: NumaStat.parse,
        PercpuStat: PercpuStat.parse,
    }
    def __init__(self, path, filters=None):
        self.path = path
        self.filters = filters

        if self.filters:
            self.configs = {}
            self.stats   = {}
            for f in self.filters:
                if f in self.CONFIGS:
                    self.configs[f] = self.CONFIGS[f]
                elif f in self.STATS:
                    self.stats[f] = self.STATS[f]
        else:
            self.configs = self.CONFIGS
            self.stats   = self.STATS
        
        self.param2path = {}
        for param in self.configs.keys()+self.stats.keys():
            attrname = 'path_'+param.replace('.', '_')
            _path = os.path.join(self.path, self.NAME+'.'+param)
            setattr(self, attrname, _path)
            self.param2path[param] = _path

    def get_configs(self):
        configs = {}
        for config, default in self.configs.iteritems():
            cls = default.__class__
            path = self.param2path[config]
            if os.path.exists(path):
                configs[config] = self.PARSERS[cls](path)
        return configs

    def get_default_configs(self):
        return self.CONFIGS.copy()

    def get_stats(self):
        stats = {}
        for stat, cls in self.stats.iteritems():
            #cls = parser.__class__
            path = self.param2path[stat]
            if os.path.exists(path):
                stats[stat] = self.PARSERS[cls](path)
        return stats

    def get_usages(self):
        usages = {}
        for stat, cls in self.stats.iteritems():
            path = self.param2path[stat]
            if os.path.exists(path):
                usages[stat] = self.PARSERS[cls](path)
        return usages

#
# Classes of each subsystem
#
class SubsystemCpu(Subsystem):
    NAME = 'cpu'
    _path_rt_period  = '/proc/sys/kernel/sched_rt_period_us'
    _path_rt_runtime = '/proc/sys/kernel/sched_rt_runtime_us'
    STATS = {
        'stat': SimpleStat,
    }
    CONFIGS = {
        'shares':        1024,
        # Are the default values correct?
        'rt_period_us':  long(readfile(_path_rt_period)),
        'rt_runtime_us': long(readfile(_path_rt_runtime)),
        'cfs_period_us': 100000,
        'cfs_quota_us': -1,
    }

class SubsystemCpuacct(Subsystem):
    NAME = 'cpuacct'
    STATS = {
        'usage': long,
        'stat': SimpleStat,
        'usage_percpu': PercpuStat,
    }
    CONFIGS = {}

class SubsystemCpuset(Subsystem):
    NAME = 'cpuset'
    STATS = {
        'memory_pressure': long,
    }
    CONFIGS = {
        'cpu_exclusive': 0,
        # str object something like '0', '0-1', and '0-1,3,4'
        'cpus': host.CPUInfo().get_online(),
        'mem_exclusive': 0,
        'mem_hardwall': 0,
        'memory_migrate': 0,
        'memory_pressure_enabled': 0,
        'memory_spread_page': 0,
        'memory_spread_slab': 0,
        # same as 'cpus'
        'mems': host.MemInfo().get_online(),
        'sched_load_balance': 1,
        'sched_relax_domain_level': -1,
    }

class SubsystemMemory(Subsystem):
    NAME = 'memory'
    STATS = {
        'failcnt': long,
        'usage_in_bytes': long,
        'max_usage_in_bytes': long,
        'memsw.failcnt': long,
        'memsw.max_usage_in_bytes': long,
        'memsw.usage_in_bytes': long,
        'stat': SimpleStat,
        'numa_stat': NumaStat,
    }
    MAX_ULONGLONG = 2**63-1
    CONFIGS = {
        'limit_in_bytes': MAX_ULONGLONG,
        'memsw.limit_in_bytes': MAX_ULONGLONG,
        'move_charge_at_immigrate': 0,
        'oom_control': SimpleStat({'oom_kill_disable':0, 'under_oom':0}),
        'soft_limit_in_bytes': MAX_ULONGLONG,
        'swappiness': 60,
        'use_hierarchy': 0,
    }

    def get_usages(self):
        usages = Subsystem.get_usages(self)

        # For convenience
        usages['total'] = usages['usage_in_bytes']
        if 'memsw.usage_in_bytes' in usages:
            usages['swap']  = usages['memsw.usage_in_bytes'] - usages['total']
        usages['rss']   = usages['stat']['rss']
        return usages

class SubsystemBlkio(Subsystem):
    NAME = 'blkio'
    STATS = {
        'io_merged': BlkioStat,
        'io_queued': BlkioStat,
        'io_service_bytes': BlkioStat,
        'io_service_time': BlkioStat,
        'io_serviced': BlkioStat,
        'io_wait_time': BlkioStat,
        'sectors': SimpleStat,
        'throttle.io_service_bytes': BlkioStat,
        'throttle.io_serviced': BlkioStat,
        'time': SimpleStat,
    }
    CONFIGS = {
        'throttle.read_iops_device': SimpleStat({}),
        'throttle.write_iops_device': SimpleStat({}),
        'throttle.read_bps_device': SimpleStat({}),
        'throttle.write_bps_device': SimpleStat({}),
        'weight': 1000,
        'weight_device': SimpleStat({}),
    }

    def get_usages(self):
        usages = Subsystem.get_usages(self)

        # For convenience
        n_reads = n_writes = 0L
        for k,v in usages['io_service_bytes'].iteritems():
            if k == 'Total': continue
            n_reads += v['Read']
            n_writes += v['Write']
        usages['read'] = n_reads
        usages['write'] = n_writes
            
        return usages

class SubsystemFreezer(Subsystem):
    NAME = 'freezer'
    STATS = {
        'state': str,
    }
    CONFIGS = {}

    def get_usages(self):
        if os.path.exists(self.path_state):
            return {'state': "%s"%(readfile(self.path_state).strip(),),}
        else:
            # Root group does not have the file
            return {'state': ''}

    get_stats = get_usages

class SubsystemNetCls(Subsystem):
    NAME = 'net_cls'
    STATS = {}
    CONFIGS = {
        'classid': 0,
    }

class SubsystemDevices(Subsystem):
    NAME = 'devices'
    STATS = {}
    CONFIGS = {
        'list': DevicesStat(['a *:* rwm']),
    }

subsystem_name2class = {
    'cpu':SubsystemCpu,
    'cpuacct':SubsystemCpuacct,
    'cpuset':SubsystemCpuset,
    'memory':SubsystemMemory,
    'blkio':SubsystemBlkio,
    'freezer':SubsystemFreezer,
    'net_cls':SubsystemNetCls,
    'devices':SubsystemDevices,
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

    def __init__(self, mount_point, path, subsystem):
        self.mount_point = mount_point
        self.path = path
        self.subsystem = subsystem

        self.fullpath = os.path.normpath(self.mount_point+path)
        if self.path == '/':
            self.depth = 0
        else:
            self.depth = self.calc_depth(self.path)
        if self.path == '/':
            self.fullname = self.name = '<root>'
        else:
            self.name = os.path.basename(self.path)
            self.fullname = self.path[1:]

        self.path_tasks = os.path.join(self.fullpath,'tasks')
        self.path_procs = os.path.join(self.fullpath,'cgroup.procs')
        self.path_release_agent = os.path.join(self.fullpath,
                                               'release_agent')
        self.path_notify_on_release = os.path.join(self.fullpath,
                                                   'notify_on_release')

        self.__update_usages()
        self._update_n_procs()

        self.childs = []

    def __str__(self):
        return "%s: subsystem=%s, name=%s, fullname=%s, mount_point=%s, path=%s, depth=%d" % \
               (self.__class__, self.subsystem, self.name, self.fullname,
                self.mount_point, self.path, self.depth)

    def update_pids(self):
        pids = readfile(self.path_procs).split('\n')[:-1]
        self.pids = [int(pid) for pid in pids]
        self.n_procs = len(pids)

    def _update_n_procs(self):
        self.n_procs = readfile(self.path_procs).count("\n") - 1
        if self.n_procs == -1: self.n_procs = 0

    def __update_usages(self):
        self.usages = self.subsystem.get_usages()

    def _update_usages(self):
        prev = self.usages
        self.__update_usages()

        def calc_delta_recursive(usage, _prev, delta):
            for k, v in usage.iteritems():
                # prev value may not be set, so have to check the existence
                if v.__class__ is not dict:
                    if k in _prev:
                        delta[k] = v - _prev[k]
                    else:
                        delta[k] = None
                    continue
                _delta = {}
                if k in _prev:
                    calc_delta_recursive(v, _prev[k], _delta)
                delta[k] = _delta

        self.usages_delta = {}
        calc_delta_recursive(self.usages, prev, self.usages_delta)

    def update(self):
        self._update_n_procs()
        self._update_usages()

    def get_usages(self):
        return self.usages.copy()

    def get_stats(self):
        return self.subsystem.get_stats()

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

def scan_cgroups_recursively0(subsystem, fullpath, mount_point, filters):
    relpath = fullpath.replace(mount_point, '')
    relpath = '/' if relpath == '' else relpath
    cgroup = CGroup(mount_point, relpath,
                    subsystem_name2class[subsystem](fullpath, filters))

    _childs = []
    for _file in os.listdir(fullpath):
        child_fullpath = os.path.join(fullpath,_file)
        if os.path.isdir(child_fullpath):
            child = scan_cgroups_recursively0(subsystem, child_fullpath,
                                                mount_point, filters)
            _childs.append(child)
    cgroup.childs.extend(_childs)
    return cgroup

def scan_cgroups_recursively(subsystem, mount_point, filters=None):
    return scan_cgroups_recursively0(subsystem, mount_point, mount_point, filters)

class NoSuchSubsystemError(StandardError): pass

def scan_cgroups(subsys):
    status = SubsystemStatus()
    if subsys not in status.get_all():
        raise NoSuchSubsystemError('No such subsystem found: %s'%(subsys,))

    if subsys not in status.get_available():
        raise EnvironmentError('Disabled in the kernel: %s'%(subsys,))

    if subsys not in status.get_enabled():
        raise EnvironmentError('Not enabled in the system: %s'%(subsys,))

    mount_point = status.get_path(subsys)
    return scan_cgroups_recursively(subsys, mount_point)

def walk_cgroups(cgroup, action, opaque):
    action(cgroup, opaque)
    for child in cgroup.childs:
        walk_cgroups(child, action, opaque)
