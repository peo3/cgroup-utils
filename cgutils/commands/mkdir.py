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

from cgutils import cgroup
from cgutils import command
from cgutils import formatter
from cgutils import host


class Command(command.Command):
    NAME = 'mkdir'

    parser = command.Command.parser
    parser.add_option('-a', '--apply-all', action='store_true',
                      dest='apply_all', default=False,
                      help='Make directories for each subsystem')
    parser.add_option('-p', '--parents', action='store_true',
                      dest='parents', default=False,
                      help='Make parent directories if not exist')
    parser.usage = "%%prog %s [options]" % NAME

    def run(self, args):
        if len(args) == 0:
            self.parser.error('Less arguments: ' + ' '.join(args))

        if self.options.debug:
            print args

        target_dir = args[0]

        cgpath = os.path.dirname(target_dir)
        new = os.path.basename(target_dir)
        if self.options.parents and not os.path.exists(cgpath):
            self.parser.error('%s not found' % cgpath)

        cg = cgroup.get_cgroup(cgpath)

        cg.mkdir(new)
