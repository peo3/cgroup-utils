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

import os

from cgutils import cgroup
from cgutils import command


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

        parent_path = os.path.dirname(target_dir)
        new = os.path.basename(target_dir)
        if self.options.parents and not os.path.exists(parent_path):
            self.parser.error('%s not found' % parent_path)

        parent = cgroup.get_cgroup(parent_path)

        if not self.options.apply_all:
            parent.mkdir(new)
        else:
            status = cgroup.SubsystemStatus()
            enabled = status.get_enabled()
            enabled = [s for s in enabled if not (s == 'perf_event' or s == 'debug')]

            parents = []
            for name in enabled:
                mount_point = status.get_path(name)
                path = os.path.join(mount_point, parent.fullname.lstrip('/'))
                parents.append(cgroup.get_cgroup(path))

            # Check directory existence first
            to_be_created = []
            for _parent in parents:
                new_path = os.path.join(_parent.fullpath, new)
                if self.options.debug:
                    print(new_path)
                if os.path.exists(new_path):
                    if not self.options.parents:
                        print("%s exists" % new_path)
                        sys.exit(1)
                    else:
                        to_be_created.append(_parent)
                else:
                    to_be_created.append(_parent)

            if self.options.debug:
                print(to_be_created)

            for _parent in to_be_created:
                if self.options.debug:
                    new_path = os.path.join(_parent.fullpath, new)
                    print("mkdir %s" % new_path)
                new_path = os.path.join(_parent.fullpath, new)
                if os.path.exists(new_path):
                    # XXX: this may happen when systemd creates
                    # a cpuacct,cpu group and links cpu and cpuacct
                    # to it.
                    continue
                _parent.mkdir(new)
