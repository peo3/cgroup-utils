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

from cgutils import cgroup
from cgutils import command
from cgutils import process


DECORATER = {
    'red': lambda s: '\033[31m' + s + '\033[0m',
    'green': lambda s: '\033[32m' + s + '\033[0m',
    'bold': lambda s: '\033[1m' + s + '\033[0m',
    'lightblue': lambda s: '\033[95m' + s + '\033[0m',
    'underline': lambda s: '\033[4m' + s + '\033[0m',
    'blink': lambda s: '\033[5m' + s + '\033[0m',
    'kthread': lambda s: '[' + s + ']',
    'cgroup': lambda s: DECORATER['bold'](DECORATER['red'](s)),
    'autogroup': lambda s: DECORATER['bold'](DECORATER['green'](s)),
    'groupleader': lambda s: DECORATER['lightblue'](s),
    'sessionleader': lambda s: DECORATER['underline'](s),
    'running': lambda s: DECORATER['blink'](s),
}


def decorate(string, type):
    return DECORATER[type](string)


class AutoGroup():
    def __init__(self, name, pids):
        self.name = name
        self.pids = pids


class TreeContainer():
    def __init__(self, this):
        self.this = this

        self.childs = []

    def __str__(self):
        return str((str(self.this), self.childs))


class Command(command.Command):
    NAME = 'tree'
    DEFAULT_SUBSYSTEM = 'cpu'

    parser = command.Command.parser
    parser.add_option('-o', action='store', type='string',
                      dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                      help='Specify a subsystem [cpu]')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups [False]')
    parser.add_option('-k', '--show-kthread', action='store_true',
                      dest='show_kthread', default=False,
                      help='Show kernel threads [False]')
    parser.add_option('-c', '--color', action='store_true',
                      dest='color', default=False,
                      help='Coloring [False]')
    parser.add_option('-i', '--show-pid', action='store_true',
                      dest='show_pid', default=False,
                      help='Show PID [False]')
    parser.add_option('-n', '--show-nprocs', action='store_true',
                      dest='show_nprocs', default=False,
                      help='Show # of processes in each cgroup [False]')
    parser.add_option('-p', '--show-procs', action='store_true',
                      dest='show_procs', default=False,
                      help='Show processes in each cgroup [False]')
    parser.add_option('-a', '--show-autogroup', action='store_true',
                      dest='show_autogroup', default=False,
                      help='Show groups by autogroup feature [False]')
    parser.usage = "%%prog %s [options]" % NAME

    _INDENT_SIZE = 4

    def _build_indent(self, indents):
        if len(indents) == 0:
            return ''
        s = ''
        for n in range(len(indents)):
            indent = indents[n]
            if indent == 'cont' and n == len(indents) - 1:
                s += ' ' * (self._INDENT_SIZE - 1) + '+'
            elif indent == 'cont':
                s += ' ' * (self._INDENT_SIZE - 1) + '|'
            elif indent == 'last' and n == len(indents) - 1:
                s += ' ' * (self._INDENT_SIZE - 1) + '`'
            else:
                s += ' ' * self._INDENT_SIZE
        return s

    def _print_process(self, proc, indents):
        s = self._build_indent(indents)
        if proc.is_kthread():
            s += decorate(proc.name, 'kthread')
        else:
            name = proc.name
            if self.options.color:
                if proc.is_group_leader():
                    name = decorate(name, 'groupleader')
                if proc.is_session_leader():
                    name = decorate(name, 'sessionleader')
                if proc.is_running():
                    name = decorate(name, 'running')
            s += name
        if self.options.show_pid:
            s += "(%d)" % proc.pid
        if self.options.debug:
            s += str(indents)
        print(s)

    def _print_cgroup(self, cg, indents):
        cg.update()
        if self.options.debug:
            print(cg.pids)
        s = self._build_indent(indents)
        if self.options.color:
            s += decorate(cg.name, 'cgroup')
        else:
            s += cg.name
        if self.options.show_nprocs:
            s += '(%d)' % cg.n_procs
        if self.options.debug:
            s += str(indents)
        print(s)

    def _print_autogroup(self, autogroup, indents):
        if self.options.debug:
            print(autogroup.pids)
        s = self._build_indent(indents)
        if self.options.color:
            s += decorate(autogroup.name, 'autogroup')
        else:
            s += autogroup.name
        if self.options.show_nprocs:
            s += "(%d)" % len(autogroup.pids)
        if self.options.debug:
            s += str(indents)
        print(s)

    def _build_process_container_tree(self, pids):
        """
        tops = [1,2,3]
        childs = {1: [4,5], 2: [6,7], 3: [], 4: []}
        """
        containers = []
        procs = []
        ppids = []
        childs = {}
        for pid in pids:
            proc = process.Process(pid)
            procs.append(proc)
            ppids.append(proc.ppid)
            if proc.ppid not in childs:
                childs[proc.ppid] = []
            childs[proc.ppid].append(proc)
        ppids = set(ppids)
        tops = [proc for proc in procs if proc.ppid not in pids]
        if len(tops) == 0:
            tops = procs

        def build_tree(proc_list):
            _containers = []
            for proc in proc_list:
                if not self.options.show_kthread and proc.is_kthread():
                    continue

                cont = TreeContainer(proc)

                if proc.pid in childs:
                    cont.childs = build_tree(childs[proc.pid])
                _containers.append(cont)
            return _containers

        for top_proc in tops:
            if not self.options.show_kthread and top_proc.is_kthread():
                continue

            cont = TreeContainer(top_proc)
            if top_proc.pid in childs:
                cont.childs = build_tree(childs[top_proc.pid])
            containers.append(cont)

        return containers

    def _build_autogroup_container_tree(self, pids):
        containers = []
        groups = {}
        for pid in pids:
            proc = process.Process(pid)
            if proc.autogroup not in groups:
                groups[proc.autogroup] = []
            groups[proc.autogroup].append(pid)

        for name, pids in groups.iteritems():
            if name is None:
                # Want to put kthreads at the tail
                continue
            if self.options.debug:
                print(name + str(pids))
            group = AutoGroup(name, pids)
            cont = TreeContainer(group)
            cont.childs = self._build_process_container_tree(group.pids)
            containers.append(cont)

        if None in groups and self.options.show_kthread:
            containers += self._build_process_container_tree(groups[None])

        return containers

    def run(self, args):
        if self.options.show_autogroup and self.options.target_subsystem != 'cpu':
            print("Error: autogroup is meaningless for %s subsystem" %
                  self.options.target_subsystem)
            sys.exit(1)

        root_cgroup = cgroup.scan_cgroups(self.options.target_subsystem)

        if self.options.debug:
            print(root_cgroup)

        def build_container_tree(container):
            _cgroup = container.this
            for child in _cgroup.childs:
                child.update()
                n_childs = len(child.childs)
                n_pids = len(child.pids)
                if self.options.hide_empty and n_childs == 0 and n_pids == 0:
                    continue
                cont = TreeContainer(child)
                container.childs.append(cont)

                build_container_tree(cont)

            if not self.options.show_procs:
                return

            _cgroup.update()
            if self.options.debug:
                print(_cgroup.pids)

            if self.options.show_autogroup and container == root_container:
                # Autogroup is effective only when processes don't belong
                # to any cgroup
                groups = self._build_autogroup_container_tree(_cgroup.pids)
                container.childs.extend(groups)
            else:
                procs = self._build_process_container_tree(_cgroup.pids)
                container.childs.extend(procs)

        root_container = TreeContainer(root_cgroup)
        build_container_tree(root_container)

        def print_containers_recursively(cont, indents):
            if self.options.debug:
                print(cont)

            if isinstance(cont.this, cgroup.CGroup):
                self._print_cgroup(cont.this, indents)
            elif isinstance(cont.this, process.Process):
                self._print_process(cont.this, indents)
            else:
                self._print_autogroup(cont.this, indents)
            for child in cont.childs:
                if child == cont.childs[-1]:
                    _indents = indents + ['last']
                else:
                    _indents = indents + ['cont']
                print_containers_recursively(child, _indents)

        print_containers_recursively(root_container, [])
