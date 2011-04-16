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
# Copyright (c) 2011 peo3 <peo314159265@gmail.com>

"""
    CPU
"""
USEC=1000*1000*1000
DAY=60*60*24
HOUR=60*60
MINUTE=60
def usec2str(sec):
    sec = float(sec)/USEC
    if sec > DAY:
        return "%.1fd"%(sec/DAY,)
    if sec > HOUR:
        return "%.1fh"%(sec/HOUR,)
    elif sec > MINUTE:
        return "%.1fm"%(sec/MINUTE,)
    else:
        return "%.1fs"%(sec,)

max_width_time = len('NNN.N_')

def percent2str(per):
    #return "%.1f %%"%(per,)
    #return "%.1f"%(per,)
    return "%.1f%%"%(per,)

max_width_percent = len('NNN.N%')
max_width_cpu = max_width_percent

"""
    Memory
"""
GiB=1024*1024*1024
MiB=1024*1024
KiB=1024
GB=1000*1000*1000
MB=1000*1000
KB=1000
def byte2str(byte):
    byte = float(byte)
    if abs(byte) > GB:
        return "%.1fG"%(byte/GiB,)
    elif abs(byte) > MB:
        return "%.1fM"%(byte/MiB,)
    elif abs(byte) > KB:
        return "%.1fk"%(byte/KiB,)
    else:
        return "%.1f "%(byte,)

max_width_byte = len('-NNN.N_')
max_width_memory = max_width_byte

"""
    Block I/O
"""
def byps2str(byte):
    byte = float(byte)
    if byte > GB:
        return "%.1fG/s"%(byte/GiB,)
    elif byte > MB:
        return "%.1fM/s"%(byte/MiB,)
    elif byte > KB:
        return "%.1fk/s"%(byte/KiB,)
    else:
        return "%.1f /s"%(byte,)

max_width_byps = len('NNN.N_/s')
max_width_blkio = max_width_byps

