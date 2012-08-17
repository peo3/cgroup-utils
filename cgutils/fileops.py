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


def read(path):
    with open(path) as f:
        return f.read()


def readlines(path):
    with open(path) as f:
        return [c.rstrip('\n') for c in f.readlines()]


def write(path, cont):
    with open(path, 'w') as f:
        return f.write(cont)


def mkdir(path, mode=0777):
    os.mkdir(path, mode)


def rmdir(path):
    os.rmdir(path)
