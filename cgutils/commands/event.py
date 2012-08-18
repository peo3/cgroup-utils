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
import os
import os.path
import time
import signal

from cgutils import cgroup
from cgutils import command
from cgutils import fileops
from cgutils import formatter


class Command(command.Command):
    NAME = 'event'

    parser = command.Command.parser
    parser.add_option('-t', '--timeout', type='float', dest='timeout_seconds',
                      help='Timeout in SEC [%default seconds]',
                      metavar='SEC', default=0.0)
    parser.usage = "%%prog %s [options] <target_file> [<argument>...]" % NAME

    def _parse_value(self, val):
        if val[-1] == 'K':
            return long(val.replace('M', '')) * 1024
        elif val[-1] == 'M':
            return long(val.replace('M', '')) * 1024 * 1024
        elif val[-1] == 'G':
            return long(val.replace('M', '')) * 1024 * 1024 * 1024
        else:
            return long(val)

    def _show_memory_usage(self, title, _cgroup):
        stats = _cgroup.get_stats()
        usage = stats['usage_in_bytes']
        print "%s: %d (%s)" % (title, usage, formatter.byte(usage))
        if 'memsw.usage_in_bytes' in stats:
            usage = stats['memsw.usage_in_bytes']
            print "%s(memsw): %d (%s)" % (title, usage, formatter(usage))

    def run(self, args):
        if len(args) == 0:
            self.parser.error('Less arguments: ' + ' '.join(args))

        if self.options.debug:
            print args

        target_file = args[0]

        if not os.path.exists(target_file):
            print "File not found: %s" % target_file
            sys.exit(1)

        target_name = os.path.basename(target_file)

        arguments = []
        if target_name in ['memory.usage_in_bytes', 'memory.memsw.usage_in_bytes']:
            self.parser.usage = "%%prog %s [options] <target_file> <threshold>" % self.NAME
            if len(args) < 2:
                self.parser.error('Less arguments: ' + ' '.join(args))

            if len(args) > 2:
                self.parser.error('Too many arguments: ' + ' '.join(args))
            threshold = args[1]

            if threshold[0] == '+':
                cur = long(fileops.read(target_file))
                threshold = threshold.replace('+', '')
                threshold = cur + self._parse_value(threshold)
            elif threshold[0] == '-':
                cur = long(fileops.read(target_file))
                threshold = threshold.replace('-', '')
                threshold = cur - self._parse_value(threshold)
            else:
                threshold = self._parse_value(threshold)

            if self.options.verbose:
                print "Threshold: %d (%s)" % (threshold, formatter.byte(threshold))

            arguments.append(threshold)

        elif target_name == 'memory.oom_control':
            self.parser.usage = "%%prog %s [options] <target_file>" % self.NAME
            if len(args) != 1:
                self.parser.error('Too many arguments: ' + ' '.join(args))

        else:
            files = ', '.join(cgroup.EventListener.SUPPORTED_FILES)
            message = "Target file not supported: %s\n" % target_name
            message += "(Supported files: %s)" % files
            self.parser.error(message)

        cg = cgroup.get_cgroup(os.path.dirname(target_file))

        if self.options.verbose:
            self._show_memory_usage('Before', cg)

        pid = os.fork()
        if pid == 0:
            listener = cgroup.EventListener(cg, target_name)
            listener.register(arguments)

            #ret = listener.wait()
            listener.wait()
            os._exit(0)

        timed_out = False
        if self.options.timeout_seconds:
            remained = self.options.timeout_seconds
            while remained > 0:
                ret = os.waitpid(pid, os.WNOHANG)

                if ret != (0, 0):
                    break
                time.sleep(0.1)
                remained -= 0.1
            else:
                timed_out = True
                os.kill(pid, signal.SIGTERM)
        else:
            os.waitpid(pid, 0)

        if not os.path.exists(cg.fullpath):
            print('The cgroup seems to have been removed.')
            sys.exit(1)

        if self.options.verbose:
            self._show_memory_usage('After', cg)

        if timed_out:
            if self.options.verbose:
                print('Timed out')
            sys.exit(2)
        else:
            sys.exit(0)
