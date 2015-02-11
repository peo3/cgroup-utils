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
# Copyright (c) 2012,2013 peo3 <peo314159265@gmail.com>

import os
import os.path

from cgutils import cgroup
from cgutils import command
from cgutils import process


class Command(command.Command):
    NAME = 'pgrep'
    HELP = 'Search and show processes with cgroup like pgrep command'
    DEFAULT_SUBSYSTEM = 'cpu'

    @staticmethod
    def add_subparser(subparsers):
        parser = subparsers.add_parser(Command.NAME, help=Command.HELP)
        parser.add_argument('-o', action='store',
                            dest='target_subsystem', default=Command.DEFAULT_SUBSYSTEM,
                            help='Specify a subsystem [%(default)s]')
        parser.add_argument('-f', '--cmdline', action='store_true',
                            help='Compare with entire cmdline of process')
        parser.add_argument('-l', '--show-name', action='store_true',
                            help='Show name of process')
        parser.add_argument('-i', '--ignore-case', action='store_true',
                            help='Ignore case')
        parser.add_argument('procname', metavar='PROCNAME', help='Process name')

    def run(self):
        root_cgroup = cgroup.scan_cgroups(self.args.target_subsystem)

        def print_matched(cg, dummy):
            mypid = os.getpid()
            cg.update()
            for pid in cg.pids:
                if pid == mypid:
                    continue
                proc = process.Process(pid)

                if self.args.cmdline:
                    comp = proc.cmdline
                else:
                    comp = proc.name

                if self.args.ignore_case:
                    comp = comp.lower()
                    _procname = self.args.procname.lower()
                else:
                    _procname = self.args.procname

                if _procname in comp:
                    if self.args.show_name:
                        if self.args.cmdline:
                            output = "%d %s" % (proc.pid, proc.cmdline)
                        else:
                            output = "%d %s" % (proc.pid, proc.name)
                    else:
                        output = str(proc.pid)
                    print('%s: %s' % (cg.path, output))

        cgroup.walk_cgroups(root_cgroup, print_matched, None)
