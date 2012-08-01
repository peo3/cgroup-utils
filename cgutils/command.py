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

import optparse

from cgutils.version import VERSION


class Command():
    NAME = 'cgutil'
    parser = optparse.OptionParser(version="%s %s" % (NAME, VERSION))
    parser.add_option('--debug', action='store_true', dest='debug',
                      default=False, help='Show debug messages')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                      default=False, help='Output extra messages')
    parser.usage = "%%prog %s [options]" % NAME

    def __init__(self, options):
        self.options = options
