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
import struct

from cgutils import host
from cgutils import linux

def readfile(filepath):
    with open(filepath) as f:
        return f.read()

class SubsystemStatus(dict):
    def __init__(self):
        dict.__init__(self)
        self.paths = {}
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

            name = None
            for opt in opts:
                if opt in self:
                    name = opt
                    self.paths[name] = path
                if 'name=' in opt:
                    # We treat name=XXX as its name
                    name = opt
                    self.paths[name] = path
                    self[name] = {}
                    self[name]['name'] = name
                    self[name]['enabled'] = True
                    self[name]['hierarchy'] = 0
                    self[name]['num_cgroups'] = 0
            # release_agent= may appear before name=
            for opt in opts:
                if 'release_agent=' in opt:
                    self[name]['release_agent'] = opt.replace('release_agent=', '')

    def _update(self):
        self._parse_proc_cgroups()
        self._parse_proc_mount()

    def update(self):
        self.clear()
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
100
103
234
"""
class SimpleList(dict):
    @staticmethod
    def parse(path):
        ret = []
        for line in readfile(path).split('\n')[:-1]:
            ret.append(long(line))
        return ret

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
        i = 0
        for stat in stats:
            ret[i] = long(stat)
            i += 1
        return ret

#
# The base class of subsystems
#
class Subsystem(object):
    CONFIGS = {}
    STATS = {}
    CONTROLS = {}
    NAME = None

    def __init__(self):
        self.name = self.NAME

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
    CONTROLS = {}

class SubsystemCpuacct(Subsystem):
    NAME = 'cpuacct'
    STATS = {
        'usage': long,
        'stat': SimpleStat,
        'usage_percpu': PercpuStat,
    }
    CONFIGS = {}
    CONTROLS = {}

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
    CONTROLS = {}

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
        'kmem.tcp.failcnt': long,
        'kmem.tcp.max_usage_in_bytes': long,
        'kmem.tcp.usage_in_bytes': long,
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
        'kmem.tcp.limit_in_bytes': MAX_ULONGLONG,
    }
    CONTROLS = {
        'force_empty': None,
    }

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
    CONTROLS = {
        'reset_stats': None,
    }

class SubsystemFreezer(Subsystem):
    NAME = 'freezer'
    STATS = {
        'state': str,
    }
    CONFIGS = {}
    CONTROLS = {}

class SubsystemNetCls(Subsystem):
    NAME = 'net_cls'
    STATS = {}
    CONFIGS = {
        'classid': 0,
    }
    CONTROLS = {}

class SubsystemDevices(Subsystem):
    NAME = 'devices'
    STATS = {}
    CONFIGS = {
        'list': DevicesStat(['a *:* rwm']),
    }
    CONTROLS = {
        'allow': None,
        'deny': None,
    }

class SubsystemName(Subsystem):
    NAME = 'name'
    STATS = {}
    CONFIGS = {}
    CONTROLS = {}

    def __init__(self, name):
        Subsystem.__init__(self)
        self.name = name

_subsystem_name2class = {
    'cpu':SubsystemCpu,
    'cpuacct':SubsystemCpuacct,
    'cpuset':SubsystemCpuset,
    'memory':SubsystemMemory,
    'blkio':SubsystemBlkio,
    'freezer':SubsystemFreezer,
    'net_cls':SubsystemNetCls,
    'devices':SubsystemDevices,
}
def _get_subsystem(name):
    if 'name=' in name:
        return SubsystemName(name)
    return _subsystem_name2class[name]()

class CGroup(object):
    STATS = {
        'tasks': SimpleList,
        'cgroup.procs': SimpleList,
    }
    CONFIGS = {
        'release_agent': '',
        # XXX: the default value is actually inherited from a parent
        'notify_on_release': 0,
        'cgroup.clone_children': 0,
    }
    CONTROLS = {
        'cgroup.event_control': None,
    }
    PARSERS = {
        int:  lambda path: int(readfile(path)),
        long: lambda path: long(readfile(path)),
        str:  lambda path: readfile(path).strip(),
        SimpleList: SimpleList.parse,
        SimpleStat: SimpleStat.parse,
        BlkioStat: BlkioStat.parse,
        DevicesStat: DevicesStat.parse,
        NumaStat: NumaStat.parse,
        PercpuStat: PercpuStat.parse,
    }

    def _calc_depth(self, path):
        def rec(path):
            rest = os.path.split(path)[0]
            if rest == '/':
                return 1
            else:
                return rec(rest) + 1
        return rec(path)

    def __init__(self, subsystem, fullpath, filters=list()):
        self.subsystem = subsystem
        self.fullpath = fullpath
        self.filters = filters

        status = SubsystemStatus()
        mount_point = status.get_path(subsystem.name)
        path = fullpath.replace(mount_point, '')
        self.path = '/' if path == '' else path

        if self.path == '/':
            self.depth = 0
            self.fullname = self.name = '<root>'
        else:
            self.depth = self._calc_depth(self.path)
            self.name = os.path.basename(self.path)
            self.fullname = self.path[1:]

        self.paths = {}
        for file in self.STATS.keys() + self.CONFIGS.keys() + self.CONTROLS.keys():
            self.paths[file] = os.path.join(self.fullpath, file)
        for file in subsystem.STATS.keys() + subsystem.CONFIGS.keys() + \
                    subsystem.CONTROLS.keys():
            self.paths[file] = os.path.join(self.fullpath, subsystem.name+'.'+file)

        self.configs = {}
        self.stats = {}

        if self.filters:
            _configs = {}
            _configs.update(self.CONFIGS)
            _configs.update(subsystem.CONFIGS)
            _stats = {}
            _stats.update(self.STATS)
            _stats.update(subsystem.STATS)
            for f in self.filters:
                if f in _configs:
                    self.configs[f] = _configs[f]
                elif f in _stats:
                    self.stats[f] = _stats[f]
        else:
            self.configs.update(self.CONFIGS)
            self.configs.update(subsystem.CONFIGS)
            self.stats.update(self.STATS)
            self.stats.update(subsystem.STATS)

        self.childs = []
        self.pids = []
        self.n_procs = 0

        self.update()

    def __str__(self):
        return "<CGroup: %s (%s)>" % (self.fullname, self.subsystem.name)

    def get_configs(self):
        configs = {}
        for name, default in self.configs.iteritems():
            cls = default.__class__
            path = self.paths[name]
            if os.path.exists(path):
                configs[name] = self.PARSERS[cls](path)
        return configs

    def get_default_configs(self):
        return self.configs.copy()

    def get_stats(self):
        stats = {}
        for name, cls in self.stats.iteritems():
            path = self.paths[name]
            if os.path.exists(path):
                stats[name] = self.PARSERS[cls](path)
        return stats

    def update(self):
        pids = readfile(self.paths['cgroup.procs']).rstrip('\n').split('\n')
        self.pids = [int(pid) for pid in pids if pid != '']
        self.n_procs = len(pids)

class EventListener(object):
    def __init__(self, cgroup, target_path):
        self.cgroup = cgroup

        # To keep the files open
        self.target_file = open(target_path)
        self.target_fd = self.target_file.fileno()

        ec_path = self.cgroup.paths['cgroup.event_control']
        self.ec_file = open(ec_path, 'w')
        self.ec_fd = self.ec_file.fileno()

        self.event_fd = linux.eventfd(0, 0)

    def set_threshold(self, threshold):
        line = "%d %d %d\0" % (self.event_fd, self.target_fd, threshold)
        os.write(self.ec_fd, line)

    def wait(self):
        ret = os.read(self.event_fd, 64/8)
        return struct.unpack('Q', ret)

def _scan_cgroups_recursive(subsystem, fullpath, mount_point, filters):
    cgroup = CGroup(subsystem, fullpath, filters)

    _childs = []
    for _file in os.listdir(fullpath):
        child_fullpath = os.path.join(fullpath, _file)
        if os.path.isdir(child_fullpath):
            child = _scan_cgroups_recursive(subsystem, child_fullpath,
                                           mount_point, filters)
            _childs.append(child)
    cgroup.childs.extend(_childs)
    return cgroup

"""
  Public APIs
"""
class NoSuchSubsystemError(StandardError): pass

def scan_cgroups(subsys_name, filters=list()):
    status = SubsystemStatus()
    if subsys_name not in status.get_all():
        raise NoSuchSubsystemError("No such subsystem found: " + subsys_name)

    if subsys_name not in status.get_available():
        raise EnvironmentError("Disabled in the kernel: " + subsys_name)

    if subsys_name not in status.get_enabled():
        raise EnvironmentError("Not enabled in the system: " + subsys_name)

    subsystem = _get_subsystem(subsys_name)
    mount_point = status.get_path(subsys_name)
    return _scan_cgroups_recursive(subsystem, mount_point, mount_point, filters)

def walk_cgroups(cgroup, action, opaque):
    action(cgroup, opaque)
    for child in cgroup.childs:
        walk_cgroups(child, action, opaque)

def get_cgroup(fullpath):
    status = SubsystemStatus()
    name = None
    for name, in status.paths.iteritems():
        if name in fullpath:
            break
    else:
        raise StandardError('Invalid path: ' + fullpath)
    subsys = _get_subsystem(name)

    return CGroup(subsys, fullpath)
