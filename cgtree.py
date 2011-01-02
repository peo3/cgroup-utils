#!/usr/bin/python

from __future__ import with_statement
import sys
import os, os.path
import re
import glob
import optparse

DEFAULT_SUBSYSTEM = 'cpu'

parser = optparse.OptionParser()
parser.add_option('-o', None, action='store', type='string', dest='target_subsystem', default=DEFAULT_SUBSYSTEM, help='Specify a subsystem')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Show detailed messages')
parser.add_option('-d', '--debug', action='store_true', dest='debug', default=False, help='Show debug messages')
(options, _args) = parser.parse_args()
if options.debug:
    print options

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
    if options.debug:
        print(name, hierarchy, n_cgroups, enabled)
    subsystem_names.append(name)
if options.debug:
    print(subsystem_names)

#
# Get path of enabled subsystems
#
subsystem2path = {}
"""
cgroup on /dev/cgroup/cpu type cgroup (rw,cpu)
"""
p = re.compile('^\w+ (?P<path>[\w/]+) cgroup (?P<opts>[\w\,]+)')
lines = readfile('/proc/mounts').split('\n')
for line in lines:
    m = p.match(line)
    if m is None: continue

    path = m.group('path')
    opts = m.group('opts').split(',')

    for opt in opts:
        if opt in subsystem_names:
            subsystem2path[opt] = path
if options.debug:
    print(subsystem2path)

if options.target_subsystem not in subsystem2path:
    print('No such subsystem: %s'%(options.target_subsystem,))
    sys.exit(1)
target_path = subsystem2path[options.target_subsystem]
mount_point = target_path

#
# Sussystems and Cgroup classes
#
class Subsystem(object):
    def __init__(self, path):
        self.path = path
    def get_content(self): pass

    def to_sec(self, usec):
        return float(usec)/1000/1000/1000

    def to_mb(self, byte):
        return float(byte)/1024/1024

class SubsystemCpuacct(Subsystem):
    def get_usage_path(self):
        return os.path.join(self.path, 'cpuacct.usage')

    def get_content(self):
        usage = int(readfile(self.get_usage_path()))
        if usage > 60*60*(1000*1000*1000):
            return "%.1fh"%(self.to_sec(usage)/60/60,)
        if usage > 60*(1000*1000*1000):
            return "%.1fm"%(self.to_sec(usage)/60,)
        else:
            return "%.1fs"%(self.to_sec(usage),)

class SubsystemMemory(Subsystem):
    def get_usage_path(self):
        return os.path.join(self.path, 'memory.usage_in_bytes')
    def get_memsw_usage_path(self):
        return os.path.join(self.path, 'memory.memsw.usage_in_bytes')

    def get_content(self):
        mem_usage = int(readfile(self.get_usage_path()))
        sw_usage = int(readfile(self.get_memsw_usage_path())) - mem_usage
        return "%.1fMB/%.1fMB"%(self.to_mb(mem_usage),self.to_mb(sw_usage))

subsystem_name2class = {
    'cpu':SubsystemCpuacct,
    'cpuacct':SubsystemCpuacct,
    'memory':SubsystemMemory,
}

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
            self.name = '<root>'
        self.subsystem = subsystem
        self.options = options

        procs = os.path.join(self.abspath,'cgroup.procs')
        self.pids = [int(pid) \
                     for pid in readfile(procs).split('\n') \
                     if pid != '']
        self.childs = []
        if self.options.debug:
            print([self.name, self.depth, self.relpath,
                   self.abspath, self.pids])

    def is_kthread(self, pid):
        #return 'VmStk' not in readfile('/proc/%d/status'%(pid,))
        return len(readfile('/proc/%d/coredump_filter'%(pid,))) == 0

    def get_cmd(self, pid):
        return readfile('/proc/%d/comm'%(pid,))[:-1]

    def __str__(self):
        meta = self.subsystem.get_content()
        cmds = sorted([self.get_cmd(pid) for pid in self.pids
                       if not self.is_kthread(pid)])
        if options.verbose:
            content = cmds
        else:
            content = '%d procs'%(len(cmds),)
        return "%s%s: %s (%s)"%('  '*self.depth, self.name, content, meta)

#
# Main
#
def scan_directory_recursively(abspath):
    if options.debug:
        print('Scanning: '+abspath)
    relpath = abspath.replace(mount_point, '')
    cgroup = CGroup(mount_point, relpath,
                    subsystem_name2class[options.target_subsystem](abspath),
                    options)

    _childs = []
    for _file in os.listdir(abspath):
        child_abspath = os.path.join(abspath,_file)
        if os.path.isdir(child_abspath):
            _childs.append(scan_directory_recursively(child_abspath))
    cgroup.childs.extend(_childs)
    return cgroup

cgroups = scan_directory_recursively(mount_point)

def print_cgroups_recursively(cgroup):
    print(cgroup)
    for child in cgroup.childs:
        print_cgroups_recursively(child)

print_cgroups_recursively(cgroups)
