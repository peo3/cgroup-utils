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


import os
import os.path

from . import fileops


class Process(object):
    def __init__(self, pid):
        self.pid = pid

        items = fileops.read('/proc/%d/stat' % pid).split(' ')
        self.name = items[1].lstrip('(').rstrip(')')
        self.state = items[2]
        self.ppid = int(items[3])
        self.pgid = int(items[4])
        self.sid = int(items[5])
        if not self.is_kthread():
            self.name = self._get_fullname()
            cmdline = fileops.read('/proc/%d/cmdline' % self.pid)
            self.cmdline = cmdline.rstrip('\0').replace('\0', ' ')
        else:
            self.cmdline = self.name

        if os.path.exists('/proc/%d/autogroup' % pid):
            autogroup = fileops.read('/proc/%d/autogroup' % pid)
        else:
            autogroup = None
        if autogroup:
            # Ex. "/autogroup-324 nice 0"
            self.autogroup = autogroup.split(' ')[0].replace('/', '')
        else:
            # kthreads don't belong to any autogroup
            self.autogroup = None

    def _get_fullname(self):
        cmdline = fileops.read('/proc/%d/cmdline' % self.pid)
        if '\0' in cmdline:
            args = cmdline.rstrip('\0').split('\0')
            # Reject empty strings, say ['', '-AOxRR', '3398.byobu']
            args = list(filter(len, args))
            if ' ' in args[0]:
                name = args[0].split(' ')[0]
            else:
                name = args[0]
        else:
            #args = [cmdline,]
            args = cmdline.split(' ')
            name = args[0]
        if name[0] == '/':
            name = os.path.basename(name)
        name = name.rstrip(':')
        if len(args) >= 2:
            scripts = ['python', 'ruby', 'perl']
            # Want to catch /usr/bin/python1.7 ...
            if len([s for s in scripts if s in name]) > 0:
                name = os.path.basename(' '.join(args[0:2]))
        return name

    def is_kthread(self):
        return self.pgid == 0 and self.sid == 0

    def is_group_leader(self):
        return self.pid == self.pgid

    def is_session_leader(self):
        return self.pid == self.sid

    def is_running(self):
        return self.state == 'R'


def exists(pid):
    return os.path.exists("/proc/%d" % pid)
