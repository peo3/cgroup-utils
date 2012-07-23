#!/usr/bin/python

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
#

from __future__ import with_statement
import sys
import os, os.path
import optparse

from cgutils import cgroup
from cgutils.version import VERSION

def readfile(target_file):
    with open(target_file) as f:
        return f.read()

def parse_value(val):
    if val[-1] == 'K':
        return long(val.replace('M', '')) * 1024
    elif val[-1] == 'M':
        return long(val.replace('M', '')) * 1024 * 1024
    elif val[-1] == 'G':
        return long(val.replace('M', '')) * 1024 * 1024 * 1024
    else:
        return long(val)


def run(args, options):
    global parser
    if len(args) < 2:
        parser.usage = 'cgutil event [options] <target_file> <threshold>'
        parser.error('Less arguments: ' + ' '.join(args))

    if options.debug:
        print args

    target_file = args[0]
    threshold = args[1]

    if not os.path.exists(target_file):
        print "File not found: %s" % target_file
        sys.exit(1)

    cg = cgroup.get_cgroup(os.path.dirname(target_file))
    listener = cgroup.EventListener(cg, target_file)

    cur = long(readfile(target_file))
    if options.debug:
        print "Before: %d (%d MB)" % (cur, cur/1024/1024)

    if threshold[0] == '+':
        threshold = threshold.replace('+', '')
        threshold = cur + parse_value(threshold)
    elif threshold[0] == '-':
        threshold = threshold.replace('-', '')
        threshold = cur - parse_value(threshold)
    else:
        threshold = parse_value(threshold)

    listener.set_threshold(threshold)

    if options.debug:
        print "Threshold: %d (%d MB)" % (threshold, threshold/1024/1024)

    ret = listener.wait()
    if not os.path.exists(cg.fullpath):
        print('The cgroup seems to have beeen removed.')
        sys.exit(1)
    if options.debug:
        cur = long(readfile(target_file))
        print "After: %d (%d MB)" % (cur, cur/1024/1024)

parser = optparse.OptionParser(version='cgutil '+VERSION)
