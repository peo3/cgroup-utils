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
# Copyright (c) 2012,2013 peo3 <peo314159265@gmail.com>
#

import sys
import os
import os.path
import time
import signal

from cgutils import cgroup
from cgutils import command
from cgutils import fileops
from cgutils import formatter


if sys.version_info.major == 3:
    long = int

class Command(command.Command):
    NAME = 'event'
    HELP = 'Wait for an event'

    @staticmethod
    def add_subparser(subparsers):
        parser = subparsers.add_parser(Command.NAME, help=Command.HELP)
        parser.add_argument('-t', '--timeout', type=float, dest='timeout_seconds',
                            help='Timeout in SEC [%(default)s seconds]',
                            metavar='SEC', default=0.0)
        parser.add_argument('target_file', metavar='TARGET_FILE', help='Target cgroup file to wait for an event')
        parser.add_argument('threshold', nargs='?', metavar='THRESHOLD',
                            help='Threshold for memory.usage_in_bytes and memory.memsw.usage_in_bytes')

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
        print("%s: %d (%s)" % (title, usage, formatter.byte(usage)))
        if 'memsw.usage_in_bytes' in stats:
            usage = stats['memsw.usage_in_bytes']
            print("%s(memsw): %d (%s)" % (title, usage, formatter(usage)))

    def run(self):
        if not os.path.exists(self.args.target_file):
            print("File not found: %s" % self.args.target_file)
            sys.exit(1)
        target_file = self.args.target_file

        target_name = os.path.basename(target_file)

        arguments = []
        if target_name in ['memory.usage_in_bytes', 'memory.memsw.usage_in_bytes']:
            if not self.args.threshold:
                self.parser.error('Less arguments: ' + ' '.join(self.args))
            threshold = self.args.threshold

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

            if self.args.verbose:
                print("Threshold: %d (%s)" % (threshold, formatter.byte(threshold)))

            arguments.append(threshold)

        elif target_name == 'memory.oom_control':
            if self.args.threshold:
                self.parser.error('Too many arguments: ' + ' '.join(self.args))

        elif target_name == 'memory.pressure_level':
            SUPPORTED_TERMS = ['low', 'medium', 'critical']
            if not self.args.threshold:
                self.parser.error('Less arguments: ' + ' '.join(self.args))
            if self.args.threshold not in SUPPORTED_TERMS:
                self.parser.error('Use one of %p' % SUPPORTED_TERMS)

            arguments.append(self.args.threshold)

        else:
            files = ', '.join(cgroup.EventListener.SUPPORTED_FILES)
            message = "Target file not supported: %s\n" % target_name
            message += "(Supported files: %s)" % files
            self.parser.error(message)

        cg = cgroup.get_cgroup(os.path.dirname(target_file))

        if self.args.verbose:
            self._show_memory_usage('Before', cg)

        pid = os.fork()
        if pid == 0:
            listener = cgroup.EventListener(cg, target_name)
            listener.register(arguments)

            #ret = listener.wait()
            listener.wait()
            os._exit(0)

        timed_out = False
        if self.args.timeout_seconds:
            remained = self.args.timeout_seconds
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

        if self.args.verbose:
            self._show_memory_usage('After', cg)

        if timed_out:
            if self.args.verbose:
                print('Timed out')
            sys.exit(2)
        else:
            sys.exit(0)
