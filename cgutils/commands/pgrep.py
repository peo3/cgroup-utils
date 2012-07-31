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
# Copyright (c) 2012 peo3 <peo314159265@gmail.com>

from __future__ import with_statement
import os
import os.path

from cgutils import cgroup
from cgutils import command
from cgutils import process


class Command(command.Command):
    NAME = 'pgrep'
    DEFAULT_SUBSYSTEM = 'cpu'
    parser = command.Command.parser
    parser.add_option('-o', action='store', type='string',
                      dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                      help='Specify a subsystem [%default]')
    parser.add_option('-f', '--cmdline', action='store_true',
                      dest='cmdline', default=False,
                      help='Compare with entire cmdline of process')
    parser.add_option('-l', '--show-name', action='store_true',
                      dest='show_name', default=False,
                      help='Show name of process')
    parser.add_option('-i', '--ignore-case', action='store_true',
                      dest='ignore_case', default=False,
                      help='Ignore case')
    parser.usage = "%%prog %s [options] <proc_name>" % NAME

    def run(self, args):
        if len(args) < 1:
            self.parser.error('Less argument')

        if len(args) > 1:
            self.parser.error('Too many arguments: ' + ' '.join(args))

        procname = args[0]
        root_cgroup = cgroup.scan_cgroups(self.options.target_subsystem)

        def print_matched(cg, dummy):
            mypid = os.getpid()
            cg.update()
            for pid in cg.pids:
                if pid == mypid:
                    continue
                proc = process.Process(pid)

                if self.options.cmdline:
                    comp = proc.cmdline
                else:
                    comp = proc.name

                if self.options.ignore_case:
                    comp = comp.lower()
                    _procname = procname.lower()
                else:
                    _procname = procname

                if _procname in comp:
                    if self.options.show_name:
                        if self.options.cmdline:
                            output = "%d %s" % (proc.pid, proc.cmdline)
                        else:
                            output = "%d %s" % (proc.pid, proc.name)
                    else:
                        output = str(proc.pid)
                    print('%s: %s' % (cg.path, output))

        cgroup.walk_cgroups(root_cgroup, print_matched, None)
