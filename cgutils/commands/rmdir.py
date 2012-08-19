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

import sys
import os
import os.path

from cgutils import cgroup
from cgutils import command


class Command(command.Command):
    NAME = 'rmdir'

    parser = command.Command.parser
    parser.add_option('-a', '--apply-all', action='store_true',
                      dest='apply_all', default=False,
                      help='Remove directories for each subsystem')
    parser.usage = "%%prog %s [options]" % NAME

    def run(self, args):
        if len(args) == 0:
            self.parser.error('Less arguments: ' + ' '.join(args))

        if self.options.debug:
            print args

        target_dir = args[0]

        if not self.options.apply_all:
            if not os.path.exists(target_dir):
                print("Error: %s not found" % target_dir)
                sys.exit(1)

            if not os.path.isdir(target_dir):
                print("Error: %s is not a directory" % target_dir)
                sys.exit(1)

            cg = cgroup.get_cgroup(target_dir)

            if cg.depth == 0:
                print("Error: %s is a root cgroup" % target_dir)
                sys.exit(1)

            cg.rmdir()
        else:
            target = cgroup.get_cgroup(target_dir)

            status = cgroup.SubsystemStatus()
            enabled = status.get_enabled()
            enabled = [s for s in enabled if not (s == 'perf_event' or s == 'debug')]

            targets = []
            for name in enabled:
                mount_point = status.get_path(name)
                path = os.path.join(mount_point, target.fullname.lstrip('/'))
                targets.append(cgroup.get_cgroup(path))

            # Check directory existence first
            for _target in targets:
                if self.options.debug:
                    print(_target.fullpath)
                if not os.path.exists(_target.fullpath):
                    print("Error: %s not found" % _target.fullpath)
                    sys.exit(1)
                if not os.path.isdir(_target.fullpath):
                    print("Error: %s is not a directory" % _target.fullpath)
                    sys.exit(1)

            for _target in targets:
                if self.options.debug:
                    print("rmdir %s" % _target.fullpath)
                if not os.path.exists(_target.fullpath):
                    # XXX: this may happen when systemd creates
                    # a cpuacct,cpu group and links cpu and cpuacct
                    # to it.
                    continue
                _target.rmdir()
