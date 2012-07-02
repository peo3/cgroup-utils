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
import sys
import os, os.path
import optparse

from cgutils import cgroup
from cgutils import process
from cgutils import host
from cgutils import formatter
from cgutils.version import VERSION

def readfile(filepath):
    with open(filepath) as f:
        return f.read()

INDENT_SIZE=4

def build_indent(indents):
    if len(indents) == 0:
        return ''
    s = ''
    for n in range(len(indents)):
        indent = indents[n]
        if indent == 'cont' and n == len(indents)-1:
            s += ' '*(INDENT_SIZE-1)+'+'
        elif indent == 'cont':
            s += ' '*(INDENT_SIZE-1)+'|'
        elif indent == 'last' and n == len(indents)-1:
            s += ' '*(INDENT_SIZE-1)+'`'
        else:
            s += ' '*INDENT_SIZE
    return s

DECORATER = {
    'red':       lambda s: '\033[31m'+s+'\033[0m',
    'bold':      lambda s: '\033[1m'+s+'\033[0m',
    'lightblue': lambda s: '\033[95m'+s+'\033[0m',
    'underline': lambda s: '\033[4m'+s+'\033[0m',
    'blink':     lambda s: '\033[5m'+s+'\033[0m',
    'kthread':       lambda s: '['+s+']',
    'cgroup':        lambda s: DECORATER['bold'](DECORATER['red'](s)),
    'groupleader':   lambda s: DECORATER['lightblue'](s),
    'sessionleader': lambda s: DECORATER['underline'](s),
    'running':       lambda s: DECORATER['blink'](s),
}
def decorate(string, type):
    return DECORATER[type](string)

def print_process(proc, indents, options):
    s = build_indent(indents)
    if proc.is_kthread():
        s += decorate(proc.name, 'kthread')
    else:
        name = proc.name
        if options.color:
            if proc.is_group_leader():
                name = decorate(name, 'groupleader')
            if proc.is_session_leader():
                name = decorate(name, 'sessionleader')
            if proc.is_running():
                name = decorate(name, 'running')
        s += name
    if options.show_pid:
        s += "(%d)"%(proc.pid,)
    if options.debug:
        s += str(indents)
    print(s)

def print_process_tree(indents, pids, options):
    """
    tops = [1,2,3]
    rels = {1: [4,5], 2: [6,7], 3: [], 4: []}
    """
    procs = []
    ppids = []
    rels = {}
    for pid in pids:
        proc = process.Process(pid)
        if options.hide_kthread and proc.is_kthread():
            continue
        procs.append(proc)
        ppids.append(proc.ppid)
        if proc.ppid not in rels:
            rels[proc.ppid] = []
        rels[proc.ppid].append(proc)
    ppids = set(ppids)
    tops = [proc for proc in procs if proc.ppid not in pids]
    if len(tops) == 0:
        tops = procs

    def print_recursively(proc_list, _indents):
        for proc in proc_list:
            if proc.pid == proc_list[-1].pid:
                __indents = _indents+['last']
            else:
                __indents = _indents+['cont']

            print_process(proc, __indents, options)

            if proc.pid in rels:
                print_recursively(rels[proc.pid], __indents)

    print_recursively(tops, indents)

def print_cgroup(cg, indents, options):
    cg.update_pids()
    if options.debug:
        print(cg.pids)
    if options.hide_empty and len(cg.pids) == 0:
        return
    s = build_indent(indents)
    if options.color:
        s += decorate(cg.name, 'cgroup')
    else:
        s += cg.name
    if options.show_nprocs:
        s += '(%d)'%(cg.n_procs,)
    if options.debug:
        s += str(indents)
    print(s)

    if options.show_procs:
        print_process_tree(indents, cg.pids, options)

def run(options):
    root_cgroup = cgroup.scan_cgroups(options.target_subsystem)

    def print_cgroups_recursively(cg, indents):
        if options.debug:
            print(cg)

        print_cgroup(cg, indents, options)
        for child in cg.childs:
            if child == cg.childs[-1]:
                _indents = indents+['last']
            else:
                _indents = indents+['cont']
            print_cgroups_recursively(child, _indents)

    print_cgroups_recursively(root_cgroup, [])

DEFAULT_SUBSYSTEM = 'cpu'

parser = optparse.OptionParser(version='cgshowconfigs '+VERSION)
parser.add_option('-o', action='store', type='string',
                  dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                  help='Specify a subsystem [cpu]')
parser.add_option('-e', '--hide-empty', action='store_true',
                  dest='hide_empty', default=False,
                  help='Hide empty groups [False]')
parser.add_option('-k', '--hide-kthread', action='store_true',
                  dest='hide_kthread', default=False,
                  help='Hide kernel threads [False]')
parser.add_option('--color', action='store_true',
                  dest='color', default=False,
                  help='Coloring [False]')
parser.add_option('-p', '--show-pid', action='store_true',
                  dest='show_pid', default=False,
                  help='Show PID [False]')
parser.add_option('-n', '--show-nprocs', action='store_true',
                  dest='show_nprocs', default=False,
                  help='Show # of processes in each cgroup [False]')
parser.add_option('-t', '--show-procs', action='store_true',
                  dest='show_procs', default=False,
                  help='Show processes in each cgroup [False]')

