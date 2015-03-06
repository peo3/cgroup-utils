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
#
# This code is based on ui.py of iotop 0.4
# Copyright (c) 2007 Guillaume Chazarain <guichaz@gmail.com>
import sys
import curses
import select
import time
import errno

from cgutils import cgroup
from cgutils import command
from cgutils import host
from cgutils import formatter


if sys.version_info.major == 3:
    long = int

class CGTopStats:
    SUBSYSTEMS = ['cpuacct', 'blkio', 'memory']
    FILTERS = {
        'cpuacct': ['stat'],
        'blkio':   ['io_service_bytes'],
        'memory':  ['usage_in_bytes', 'memsw.usage_in_bytes', 'stat'],
    }

    def __init__(self, options):
        self.options = options

        self.hostcpuinfo = host.CPUInfo()

        self.deltas = {}
        self.prevs = {}

        self.deltas['cpu'] = 0
        self.deltas['time'] = 0

        self.cgroups = {}
        self.nosubsys_warning_showed = {}
        self._update_cgroups()
        self.last_update_cgroups = time.time()

    def _update_cgroups(self):
        def collect_by_name(cg, store):
            if cg.fullname not in store:
                store[cg.fullname] = []
            store[cg.fullname].append(cg)

        # Collect cgroups by group name (path)
        cgroups = {}
        for name in self.SUBSYSTEMS:
            try:
                root_cgroup = cgroup.scan_cgroups(name, self.FILTERS[name])
                cgroup.walk_cgroups(root_cgroup, collect_by_name, cgroups)
            except EnvironmentError as e:
                # Don't annoy users by showing error messages
                pass
            except cgroup.NoSuchSubsystemError as e:
                # Some systems don't support all subsystems, for example
                # Parallels Cloud Server and OpenVZ may not have memory subsystem.
                if name not in self.nosubsys_warning_showed:
                    print(e)
                    time.sleep(1)
                    self.nosubsys_warning_showed[name] = True
        self.cgroups = cgroups

        if self.options.hide_root:
            del self.cgroups['/']

    def _get_skelton_stats(self, name, n_procs):
        return {
            'name': name,
            'n_procs': n_procs,
            'cpu.user': 0.0,
            'cpu.system': 0.0,
            'bio.read':  0.0,
            'bio.write': 0.0,
            'mem.total': 0,
            'mem.rss': 0,
            'mem.swap':  0,
        }

    def get_cgroup_stats(self):
        cgroup_stats = []
        for cgroup_list in list(self.cgroups.values()):
            cpu = mem = bio = None
            pids = []
            for _cgroup in cgroup_list:
                subsys_name = _cgroup.subsystem.name
                if subsys_name == 'cpuacct':
                    cpu = _cgroup
                elif subsys_name == 'memory':
                    mem = _cgroup
                elif subsys_name == 'blkio':
                    bio = _cgroup
                _cgroup.update()
                pids += _cgroup.pids

            n_procs = len(set(pids))
            if not self.options.show_empty and n_procs == 0:
                continue

            active = False
            stats = self._get_skelton_stats(_cgroup.fullname, n_procs)

            if cpu:
                def percent(delta):
                    return float(delta) * 100 / self.deltas['cpu']

                if self.deltas['cpu'] and cpu in self.deltas:
                    stats['cpu.user'] = percent(self.deltas[cpu]['user'])
                    stats['cpu.system'] = percent(self.deltas[cpu]['system'])
                if (stats['cpu.user'] + stats['cpu.system']) > 0.0:
                    active = True

            if bio:
                def byps(delta):
                    return float(delta) / self.deltas['time']
                if self.deltas['time'] and bio in self.deltas:
                    stats['bio.read'] = byps(self.deltas[bio]['read'])
                    stats['bio.write'] = byps(self.deltas[bio]['write'])
                if (stats['bio.read'] + stats['bio.write']) > 0.0:
                    active = True

            if mem:
                if mem in self.deltas:
                    stats['mem.total'] = self.deltas[mem]['total']
                    stats['mem.rss'] = self.deltas[mem]['rss']
                    if 'swap' in self.deltas[mem]:
                        stats['mem.swap'] = self.deltas[mem]['swap']
                n = [stats['mem.total'],
                     stats['mem.rss'],
                     stats['mem.swap']].count(0)
                if n != 3:
                    active = True
            if not self.options.show_inactive and not active:
                pass
            else:
                cgroup_stats.append(stats)
        return cgroup_stats

    def __conv_blkio_stats(stats):
        n_reads = n_writes = long(0)
        for k, v in stats['io_service_bytes'].items():
            if k == 'Total':
                continue
            n_reads += v['Read']
            n_writes += v['Write']
        return {
            'read': n_reads,
            'write': n_writes,
        }

    def __conv_memory_stats(stats):
        _stats = {}
        _stats['total'] = stats['usage_in_bytes']
        if 'memsw.usage_in_bytes' in stats:
            _stats['swap'] = stats['memsw.usage_in_bytes'] - _stats['total']
        _stats['rss'] = stats['stat']['rss']
        return _stats

    def __conv_cpu_stats(stats):
        return {
            'user': stats['stat']['user'],
            'system': stats['stat']['system'],
        }

    _convert = {
        'memory': __conv_memory_stats,
        'cpuacct': __conv_cpu_stats,
        'blkio': __conv_blkio_stats,
    }

    def __calc_delta(current, previous):
        delta = {}
        for name, value in current.items():
            if isinstance(value, long):
                delta[name] = value - previous[name]
        return delta

    _diff = {
        long: lambda a, b: a - b,
        int: lambda a, b: a - b,
        float: lambda a, b: a - b,
        dict: __calc_delta,
    }

    def _update_delta(self, key, new):
        if key in self.prevs:
            self.deltas[key] = self._diff[new.__class__](new, self.prevs[key])
        self.prevs[key] = new

    def update(self):
        elapsed = time.time() - self.last_update_cgroups
        if elapsed > self.options.update_cgroups_interval:
            # Update cgroups hierarchy to know newcomers
            self._update_cgroups()
            self.last_update_cgroups = time.time()

        removed_group_names = []
        # Read stats from cgroups and calculate deltas
        for name, cgroup_list in self.cgroups.items():
            try:
                for _cgroup in cgroup_list:
                    _cgroup.update()
                    stats = _cgroup.get_stats()
                    if self.options.debug:
                        print(stats)
                    stats = self._convert[_cgroup.subsystem.name](stats)
                    self._update_delta(_cgroup, stats)
            except IOError as e:
                if e.args and e.args[0] == errno.ENOENT:
                    removed_group_names.append(name)

        for name in removed_group_names:
            del self.cgroups[name]

        # Calculate delta of host total CPU usage
        cpu_total_usage = self.hostcpuinfo.get_total_usage()
        self._update_delta('cpu', cpu_total_usage)

        # Calculate delta of time
        self._update_delta('time', time.time())


class CGTopUI:
    SORTING_KEYS = [
        'cpu.user',
        'cpu.system',
        'bio.read',
        'bio.write',
        'mem.total',
        'mem.rss',
        'mem.swap',
        'n_procs',
        'name',
    ]

    def __init__(self, win, cgstats, options):
        self.cgstats = cgstats
        self.options = options

        self.sorting_key = 'cpu.user'
        self.sorting_reverse = True

        self._init_display_params()
        self._init_subsys_title()
        self._init_item_titles()

        if not self.options.batch:
            self.win = win
            self.resize()
            try:
                curses.use_default_colors()
                curses.start_color()
                curses.curs_set(0)
            except curses.error:
                # This call can fail with misconfigured terminals, for example
                # TERM=xterm-color. This is harmless
                pass

    def reverse_sorting(self):
        self.sorting_reverse = not self.sorting_reverse

    def adjust_sorting_key(self, delta):
        now = self.SORTING_KEYS.index(self.sorting_key)
        new = now + delta
        new = max(0, new)
        new = min(len(CGTopUI.SORTING_KEYS) - 1, new)
        self.sorting_key = self.SORTING_KEYS[new]

    def handle_key(self, key):
        def toggle_show_inactive():
            self.options.show_inactive = not self.options.show_inactive

        def toggle_show_zero():
            self.options.show_zero = not self.options.show_zero

        def toggle_show_empty():
            self.options.show_empty = not self.options.show_empty

        key_bindings = {
            ord('q'): lambda: sys.exit(0),
            ord('Q'): lambda: sys.exit(0),
            ord('r'): lambda: self.reverse_sorting(),
            ord('R'): lambda: self.reverse_sorting(),
            ord('i'): toggle_show_inactive,
            ord('I'): toggle_show_inactive,
            ord('z'): toggle_show_zero,
            ord('Z'): toggle_show_zero,
            ord('e'): toggle_show_empty,
            ord('E'): toggle_show_empty,
            curses.KEY_LEFT: lambda: self.adjust_sorting_key(-1),
            curses.KEY_RIGHT: lambda: self.adjust_sorting_key(1),
            curses.KEY_HOME: lambda: self.adjust_sorting_key(-len(self.SORTING_KEYS)),
            curses.KEY_END: lambda: self.adjust_sorting_key(len(self.SORTING_KEYS)),
        }

        action = key_bindings.get(key, lambda: None)
        action()

    def resize(self):
        self.height, self.width = self.win.getmaxyx()

    def run(self):
        iterations = 0
        poll = select.poll()
        if not self.options.batch:
            poll.register(sys.stdin.fileno(), select.POLLIN | select.POLLPRI)
        while self.options.iterations is None or iterations < self.options.iterations:
            bef = time.time()
            self.cgstats.update()
            aft = time.time()

            debug_msg = "%.1f msec to collect statistics" % ((aft - bef) * 1000)
            self.refresh_display(debug_msg)

            if self.options.iterations:
                iterations += 1
                if iterations >= self.options.iterations:
                    break
            elif iterations == 0:
                iterations = 1

            try:
                events = poll.poll(self.options.delay_seconds * 1000.0)
            except select.error as e:
                if e.args and e.args[0] == errno.EINTR:
                    events = 0
                else:
                    raise
            if not self.options.batch:
                self.resize()
            if events:
                key = self.win.getch()
                self.handle_key(key)

    def _init_display_params(self):
        subsys_sep_size = 2
        self.SUBSYS_SEP = ' ' * subsys_sep_size
        item_sep_size = 1
        self.ITEM_SEP = ' ' * item_sep_size
        self.ITEM_WIDTHS = {
            'cpuacct':    formatter.max_width_cpu,
            'blkio':      formatter.max_width_blkio,
            'memory':     formatter.max_width_memory,
            'cpu.user':   formatter.max_width_cpu,
            'cpu.system': formatter.max_width_cpu,
            'bio.read':   formatter.max_width_blkio,
            'bio.write':  formatter.max_width_blkio,
            'mem.total':  formatter.max_width_memory,
            'mem.rss':    formatter.max_width_memory,
            'mem.swap':   formatter.max_width_memory,
            'n_procs':    3,
            'name':       0,
        }
        self.N_ITEMS = {'cpuacct': 2, 'blkio': 2,
                        'memory': 3, 'n_procs': 1, 'name': 1}

    def _init_subsys_title(self):
        title_list = []
        for name in self.cgstats.SUBSYSTEMS:
            width = self.ITEM_WIDTHS[name] * self.N_ITEMS[name] + self.N_ITEMS[name] - 1
            title = '[' + name.upper().center(width - 2) + ']'
            title_list.append(title)
        self.SUBSYS_TITLE = self.SUBSYS_SEP.join(title_list)

    def _init_item_titles(self):
        w = self.ITEM_WIDTHS
        sep = self.ITEM_SEP
        titles = []
        titles.append(sep.join([
            'USR'.center(w['cpu.user']),
            'SYS'.center(w['cpu.system']),
        ]))
        titles.append(sep.join([
            'READ'.center(w['bio.read']),
            'WRITE'.center(w['bio.write']),
        ]))
        titles.append(sep.join([
            'TOTAL'.center(w['mem.total']),
            'RSS'.center(w['mem.rss']),
            'SWAP'.center(w['mem.swap']),
        ]))
        titles.append(sep.join([
            '#'.rjust(w['n_procs']),
            'NAME'.rjust(w['name']),
        ]))
        self.ITEM_TITLE = self.SUBSYS_SEP.join(titles)
        self.KEY2TITLE = {
            'cpu.user':   'USR',
            'cpu.system': 'SYS',
            'bio.read':   'READ',
            'bio.write':  'WRITE',
            'mem.total':  'TOTAL',
            'mem.rss':    'RSS',
            'mem.swap':   'SWAP',
            'n_procs':    '#',
            'name':       'NAME',
        }

    def refresh_display(self, debug_msg):
        def format(stats):
            w = self.ITEM_WIDTHS
            sep = self.ITEM_SEP
            strs = []

            item2formatters = {
                'cpu.user':   formatter.percent,
                'cpu.system': formatter.percent,
                'bio.read':   formatter.bytepersec,
                'bio.write':  formatter.bytepersec,
                'mem.total':  formatter.byte,
                'mem.rss':    formatter.byte,
                'mem.swap':   formatter.byte,
            }

            def to_s(name):
                if not self.options.show_zero and stats[name] == 0:
                    return ' '.rjust(w[name])
                else:
                    return item2formatters[name](stats[name]).rjust(w[name])
            strs.append(sep.join([to_s('cpu.user'), to_s('cpu.system'), ]))
            strs.append(sep.join([to_s('bio.read'), to_s('bio.write'), ]))
            strs.append(sep.join([to_s('mem.total'), to_s('mem.rss'),
                                  to_s('mem.swap'), ]))
            strs.append(sep.join([
                str(stats['n_procs']).rjust(w['n_procs']),
                stats['name']]
            ))
            return self.SUBSYS_SEP.join(strs)

        cgroup_stats = self.cgstats.get_cgroup_stats()
        cgroup_stats.sort(key=lambda st: st[self.sorting_key],
                          reverse=self.sorting_reverse)
        lines = [format(s) for s in cgroup_stats]

        if self.options.batch:
            print(debug_msg)
            print(self.SUBSYS_TITLE)
            print(self.ITEM_TITLE)
            for l in lines:
                print(l)
            sys.stdout.flush()
            return

        self.win.erase()
        n_lines = 0
        if self.options.debug:
            self.win.addstr(debug_msg[:self.width])
            n_lines += 1

        self.win.hline(n_lines, 0, ord(' ') | curses.A_REVERSE, self.width)
        n_lines += 1
        attr = curses.A_REVERSE
        self.win.addstr(self.SUBSYS_TITLE, attr)

        self.win.hline(n_lines, 0, ord(' ') | curses.A_REVERSE, self.width)
        n_lines += 1
        status_msg = ''
        key_title = self.KEY2TITLE[self.sorting_key]
        pre, post = self.ITEM_TITLE.split(key_title)
        self.win.addstr(pre, curses.A_REVERSE)
        self.win.addstr(key_title, curses.A_BOLD | curses.A_REVERSE)
        self.win.addstr(post, curses.A_REVERSE)

        rest_lines = self.height - n_lines - int(bool(status_msg))
        num_lines = min(len(lines), rest_lines)
        for i in range(num_lines):
            try:
                self.win.insstr(i + n_lines, 0, lines[i].encode('utf-8'))
            except curses.error:
                exc_type, value, traceback = sys.exc_info()
                value = '%s win:%s i:%d line:%s' % \
                        (value, self.win.getmaxyx(), i, lines[i])
                value = str(value).encode('string_escape')
                raise exc_type(value).with_traceback(traceback)
        if status_msg:
            self.win.insstr(self.height - 1, 0, status_msg, curses.A_BOLD)
        self.win.refresh()


class Command(command.Command):
    NAME = 'top'
    HELP = 'Show cgroup activities like top command'

    @staticmethod
    def add_subparser(subparsers):
        parser = subparsers.add_parser(Command.NAME, help=Command.HELP)
        parser.add_argument('-i', '--show-inactive', action='store_true',
                            help='Show inactive groups')
        parser.add_argument('-z', '--show-zero', action='store_true',
                            help='Show zero numbers')
        parser.add_argument('-e', '--show-empty', action='store_true',
                            help='Hide empty groups')
        parser.add_argument('-r', '--hide-root', action='store_true',
                            help='Hide the root group')
        parser.add_argument('-b', '--batch', action='store_true',
                            help='non-interactive mode')
        parser.add_argument('-n', '--iter', type=int, dest='iterations', metavar='NUM',
                            help='Number of iterations before ending [infinite]')
        parser.add_argument('-d', '--delay', type=float, dest='delay_seconds',
                            help='Delay between iterations [%(default)s seconds]',
                            metavar='SEC', default=3.0)
        parser.add_argument('-u', '--update-cgroups-interval', type=float,
                            help='Update cgroups in every this interval [%(default)s seconds]',
                            metavar='SEC', default=10.0)

    def _run_window(self, win):
        cgstats = CGTopStats(self.args)
        ui = CGTopUI(win, cgstats, self.args)
        ui.run()

    def run(self):
        if self.args.batch:
            return self._run_window(None)
        else:
            return curses.wrapper(self._run_window)
