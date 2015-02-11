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
# Copyright (c) 2011-2013 peo3 <peo314159265@gmail.com>


import os
import os.path
import re
import multiprocessing

from . import fileops


class CPUInfo():
    def get_online(self):
        return fileops.read("/sys/devices/system/cpu/online").strip()

    def get_total_usage(self):
        line = fileops.readlines('/proc/stat')[0]
        line = line[5:]  # get rid of 'cpu  '
        usages = [int(x) for x in line.split(' ')]
        return sum(usages) / multiprocessing.cpu_count()


class MemInfo(dict):
    def get_online(self):
        if not os.path.exists('/sys/devices/system/node/'):
            return '0'
        else:
            return fileops.read('/sys/devices/system/node/online').strip()

    _p = re.compile('^(?P<key>[\w\(\)]+):\s+(?P<val>\d+)')

    def _update(self):
        for line in fileops.readlines('/proc/meminfo'):
            m = self._p.search(line)
            if m:
                self[m.group('key')] = int(m.group('val')) * 1024

    def _calc(self):
        self['MemUsed'] = self['MemTotal'] - self['MemFree'] - self['Buffers'] - self['Cached']
        self['SwapUsed'] = self['SwapTotal'] - self['SwapFree'] - self['SwapCached']
        self['MemKernel'] = self['Slab'] + self['KernelStack'] + self['PageTables'] + self['VmallocUsed']

    def update(self):
        self._update()
        self._calc()
