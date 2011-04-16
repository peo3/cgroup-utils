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
import sys
import os, os.path
import re
import glob
import optparse
try:
    import multiprocessing
except ImportError:
    # For python 2.5 or older
    class Multiprocessing:
        def cpu_count(self):
            return len(readfile('/proc/cpuinfo').split('CPU')) -1
    multiprocessing = Multiprocessing()

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
    #if options.debug:
    #    print(name, hierarchy, n_cgroups, enabled)
    subsystem_names.append(name)
#if options.debug:
#    print(subsystem_names)

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
#if options.debug:
#    print(subsystem2path)

#if options.target_subsystem not in subsystem2path:
#    print('No such subsystem: %s'%(options.target_subsystem,))
#    sys.exit(1)
#target_path = subsystem2path[options.target_subsystem]
#target_path = subsystem2path[options.target_subsystem]
#mount_point = target_path

#
# Sussystems and Cgroup classes
#
class Subsystem(object):
    def __init__(self, path):
        self.path = path
    def get_status(self): return ''
    def get_global_status(self): return ''
    def get_legend(self): return ''

class HostCPUInfo():
    def __init__(self):
        self._update()
        self._total_usage_prev = self.total_usage
    def _update(self):
        line = readfile('/proc/stat').split('\n')[0]
        line = line[5:] # get rid of 'cpu  '
        usages = map(lambda x: int(x), line.split(' '))
        self.total_usage = sum(usages)/multiprocessing.cpu_count()
        # Total ticks
        #self.total_usage = int(line.split(' ')[5])
    def update(self):
        self._total_usage_prev = self.total_usage
        self._update()
    def get_total_usage_delta(self):
        return self.total_usage - self._total_usage_prev

class SubsystemCpuacct(Subsystem):
    def __init__(self, path):
        self.path = path
        self.path_usage = os.path.join(self.path, 'cpuacct.usage')
        self.path_stat  = os.path.join(self.path, 'cpuacct.stat')

    def get_usages(self):
        usage = int(readfile(self.path_usage))
        user, system = readfile(self.path_stat).split('\n')[:2]
        return {'user': int(user.split(' ')[1]),
                'system': int(system.split(' ')[1]),
                'usage': usage}

    def get_status(self):
        usage = self.get_usages()['usage']
        s = usec2str(usage)
        return s.rjust(6)

    def get_legend(self):
        return "Consumed CPU time"

class HostMemInfo(dict):
    _p = re.compile('^(?P<key>[\w\(\)]+):\s+(?P<val>\d+)')
    def _update(self):
        for line in readfile('/proc/meminfo').split('\n'):
            m = self._p.search(line)
            if m:
                self[m.group('key')] = int(m.group('val'))*1024

    def _calc(self):
        self['MemUsed'] = self['MemTotal'] - self['MemFree'] - \
                          self['Buffers'] - self['Cached']
        self['SwapUsed'] = self['SwapTotal'] - self['SwapFree'] - \
                           self['SwapCached']
        self['MemKernel'] = self['Slab'] + self['KernelStack'] + \
                            self['PageTables'] + self['VmallocUsed']
    def update(self):
        self._update()
        self._calc()

class SubsystemMemory(Subsystem):
    _p = re.compile('rss (?P<val>\d+)')
    def __init__(self, path):
        self.path = path
        self.path_usage = os.path.join(self.path, 'memory.usage_in_bytes')
        self.path_memsw_usage = os.path.join(self.path, 'memory.memsw.usage_in_bytes')
        self.path_stat = os.path.join(self.path, 'memory.stat')

        self.meminfo = HostMemInfo()

    def get_rss(self):
        cont = readfile(self.path_stat)
        return int(self._p.search(cont).group('val'))

    def get_legend(self):
        return "TotalUsed, RSS, SwapUsed"

    def get_usages(self):
        usages = {}
        usages['total'] = int(readfile(self.path_usage))
        usages['swap']  = int(readfile(self.path_memsw_usage)) - usages['total']
        usages['rss']   = self.get_rss()
        return usages

    def get_status(self):
        usages = self.get_usages()
        vals = [usages['total'],usages['rss'],usages['swap']]
        return ','.join([byte2str(val).rjust(8) for val in vals])

    def get_global_status(self):
        meminfo = self.meminfo.update()
        return "Total=%s, Used(w/o buffer/cache)=%s, SwapUsed=%s"% \
               (byte2str(meminfo['MemTotal']),
                byte2str(meminfo['MemUsed']),
                byte2str(meminfo['SwapUsed']))

class SubsystemBlkio(Subsystem):
    def __init__(self, path):
        self.path = path
        self.path_io_service = os.path.join(self.path, 'blkio.io_service_bytes')

    def get_usages(self):
        usages = {'read':0, 'write':0}
        for line in readfile(self.path_io_service).split('\n'):
            try:
                (dev,type,bytes) = line.split(' ')
            except ValueError:
                # The last line consists of two items; we can ignore it.
                break
            if type == 'Read':  usages['read'] += int(bytes)
            if type == 'Write': usages['write'] += int(bytes)
        return usages

    def get_legend(self):
        return "Read, Write"

    def get_status(self):
        usages = self.get_usages()
        vals = [usages['read'],usages['write']]
        return ','.join([byte2str(val).rjust(8) for val in vals])

class SubsystemFreezer(Subsystem):
    def __init__(self, path):
        self.path = path
        self.path_state = os.path.join(self.path, 'freezer.state')

    def get_status(self):
        try:
            return "%s"%(readfile(self.path_state).strip(),)
        except IOError:
            # Root group does not have the file
            return ''

subsystem_name2class = {
    'cpu':SubsystemCpuacct,
    'cpuacct':SubsystemCpuacct,
    'memory':SubsystemMemory,
    'blkio':SubsystemBlkio,
    'freezer':SubsystemFreezer,
}
subsystem_class2name = {}
for name, _class in subsystem_name2class.iteritems():
    subsystem_class2name[_class] = name
# XXX
subsystem_class2name[SubsystemCpuacct] = 'cpuacct'

class CGroup(object):
    def calc_depth(self, path):
        def rec(path):
            rest = os.path.split(path)[0]
            if rest == '/': return 1
            else: return rec(rest) + 1
        return rec(path)

    def __init__(self, mount_point, relpath, subsystem, options):
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
        self.options = options

        self.childs = []
        #if self.options.debug:
        #    print([self.name, self.depth, self.relpath,
        #           self.abspath, self.pids])

        self.__update_usages()

    def _update_pids(self):
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

    def is_kthread(self, pid):
        #return 'VmStk' not in readfile('/proc/%d/status'%(pid,))
        return len(readfile('/proc/%d/coredump_filter'%(pid,))) == 0

    def get_cmd(self, pid):
        return readfile('/proc/%d/comm'%(pid,))[:-1]

    def __str__(self):
        status = self.subsystem.get_status()
        if self.options.show_pid:
            cmds = sorted(["%s(%d)"%(self.get_cmd(pid),pid)
                           for pid in self.pids
                           if not self.is_kthread(pid)])
        else:
            cmds = sorted([self.get_cmd(pid)
                           for pid in self.pids
                           if not self.is_kthread(pid)])
        if self.options.verbose:
            procs = cmds
            return "%s%s: %s"%('  '*self.depth, self.name, cmds)
        else:
            procs = ('%d procs'%(len(cmds),)).rjust(10)
            proc_indent = 12
            status_indent = 24
            s = "%s%s:"%('  '*self.depth, self.name)
            indent = proc_indent-len(s)
            if indent < 0: indent = 0
            s = "%s%s%s"%(s,' '*indent, procs)
            indent = status_indent-len(s)
            if indent < 0: indent = 0
            s = "%s%s(%s)"%(s,' '*indent, status)
            return s

def scan_directory_recursively(subsystem, options, abspath, mount_point):
    #if options.debug:
    #    print('Scanning: '+abspath)
    relpath = abspath.replace(mount_point, '')
    cgroup = CGroup(mount_point, relpath,
                    subsystem_name2class[subsystem](abspath),
                    options)

    _childs = []
    for _file in os.listdir(abspath):
        child_abspath = os.path.join(abspath,_file)
        if os.path.isdir(child_abspath):
            child = scan_directory_recursively(subsystem, options, child_abspath, mount_point)
            _childs.append(child)
    cgroup.childs.extend(_childs)
    return cgroup

def walk_cgroups(cgroup, action, opaque):
    action(cgroup, opaque)
    for child in cgroup.childs:
        walk_cgroups(child, action, opaque)
