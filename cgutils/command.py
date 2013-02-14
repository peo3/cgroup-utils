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
# Copyright (c) 2012,2013 peo3 <peo314159265@gmail.com>

import argparse

from cgutils.version import VERSION


class Command():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--debug', action='store_true', help='Show debug messages')
    parser.add_argument('-v', '--verbose', action='store_true', help='Output extra messages')

    def __init__(self):
        self.args = self.parser.parse_args()

    @staticmethod
    def add_subparser(subparsers):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError
