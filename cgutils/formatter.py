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

#
# CPU
#
USEC = 1000 * 1000 * 1000
DAY = 60 * 60 * 24
HOUR = 60 * 60
MINUTE = 60


def usec(sec):
    sec = float(sec) / USEC
    if sec > DAY:
        return "%.1fd" % (sec / DAY)
    if sec > HOUR:
        return "%.1fh" % (sec / HOUR)
    elif sec > MINUTE:
        return "%.1fm" % (sec / MINUTE)
    else:
        return "%.1fs" % sec


max_width_time = len('NNN.N_')


def percent(per):
    return "%.1f%%" % per


max_width_percent = len('NNN.N%')
max_width_cpu = max_width_percent


#
# Memory
#
GiB = 1024 * 1024 * 1024
MiB = 1024 * 1024
KiB = 1024
GB = 1000 * 1000 * 1000
MB = 1000 * 1000
KB = 1000


def byte(_byte):
    _byte = float(_byte)
    if abs(_byte) > GB:
        return "%.1fG" % (_byte / GiB)
    elif abs(_byte) > MB:
        return "%.1fM" % (_byte / MiB)
    elif abs(_byte) > KB:
        return "%.1fk" % (_byte / KiB)
    else:
        return "%.1f " % _byte


max_width_byte = len('-NNN.N_')
max_width_memory = max_width_byte


#
# Block I/O
#
def bytepersec(_byte):
    _byte = float(_byte)
    if _byte > GB:
        return "%.1fG/s" % (_byte / GiB)
    elif _byte > MB:
        return "%.1fM/s" % (_byte / MiB)
    elif _byte > KB:
        return "%.1fk/s" % (_byte / KiB)
    else:
        return "%.1f /s" % _byte


max_width_byps = len('NNN.N_/s')
max_width_blkio = max_width_byps
