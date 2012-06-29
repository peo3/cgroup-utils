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

import os, os.path

def readfile(filepath):
    with open(filepath) as f:
        return f.read()

class Process(object):
    def __init__(self, pid):
        self.pid = pid

        items = readfile('/proc/%d/stat'%(pid,)).split(' ')
        self.name = items[1].lstrip('(').rstrip(')')
        self.state = items[2]
        self.ppid = int(items[3])
        self.pgid = int(items[4])
        self.sid  = int(items[5])
        if not self.is_kthread():
            self.name = self._get_fullname()

    def _get_fullname(self):
        cmdline = readfile('/proc/%d/cmdline'%(self.pid,))
        if '\0' in cmdline:
            args = cmdline.split('\0')
        else:
            args = cmdline.split(' ')
        name = os.path.basename(args[0]).rstrip(':')
        if len(args) >= 2:
            scripts = ['python', 'ruby', 'perl']
            # Want to catch /usr/bin/python1.7 ...
            if len(filter(lambda x: x in name, scripts)) > 0:
                name = os.path.basename(args[1])
        return name

    def is_kthread(self):
        return self.pgid == 0 and self.sid == 0

    def is_group_leader(self):
        return self.pid == self.pgid

    def is_session_leader(self):
        return self.pid == self.sid

    def is_running(self):
        return self.state == 'R'

