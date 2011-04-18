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
# Copyright (c) 2011 peo3 <peo314159265@gmail.com>
#
# This code is based on ui.py of iotop 0.4
# Copyright (c) 2007 Guillaume Chazarain <guichaz@gmail.com>

import sys
import curses
import select
import locale
import optparse
import time
import errno

import cgroup
import formatter

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

    def __init__(self, win, cgroups, options):
        self.cgroups = cgroups
        self.options = options

        self.hostcpuinfo = cgroup.HostCPUInfo()
        self.last_time   = time.time()

        self.delay = 0.0
        self.cpu_delta = 0
        self.time_delta = 0

        self.sorting_key = 'name'
        self.sorting_reverse = False
        self.hide_inactive = options.hide_inactive
        self.hide_zero = options.hide_zero
        self.hide_empty = options.hide_empty

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
        def toggle_hide_inactive():
            self.hide_inactive = not self.hide_inactive

        def toggle_hide_zero():
            self.hide_zero = not self.hide_zero

        def toggle_hide_empty():
            self.hide_empty = not self.hide_empty

        key_bindings = {
            ord('q'):
                lambda: sys.exit(0),
            ord('Q'):
                lambda: sys.exit(0),
            ord('r'):
                lambda: self.reverse_sorting(),
            ord('R'):
                lambda: self.reverse_sorting(),
            ord('i'):
                toggle_hide_inactive,
            ord('I'):
                toggle_hide_inactive,
            ord('z'):
                toggle_hide_zero,
            ord('Z'):
                toggle_hide_zero,
            ord('e'):
                toggle_hide_empty,
            ord('E'):
                toggle_hide_empty,
            curses.KEY_LEFT:
                lambda: self.adjust_sorting_key(-1),
            curses.KEY_RIGHT:
                lambda: self.adjust_sorting_key(1),
            curses.KEY_HOME:
                lambda: self.adjust_sorting_key(-len(self.SORTING_KEYS)),
            curses.KEY_END:
                lambda: self.adjust_sorting_key(len(self.SORTING_KEYS)),
        }

        action = key_bindings.get(key, lambda: None)
        action()

    def resize(self):
        self.height, self.width = self.win.getmaxyx()

    def run(self):
        iterations = 0
        poll = select.poll()
        if not self.options.batch:
            poll.register(sys.stdin.fileno(), select.POLLIN|select.POLLPRI)
        while self.options.iterations is None or \
              iterations < self.options.iterations:

            removed_group_names = []

            bef = time.time()
            for name, cgroup_list in self.cgroups.iteritems():
                try:
                    for _cgroup in cgroup_list:
                        _cgroup.update()
                except IOError, e:
                    if e.args and e.args[0] == errno.ENOENT:
                        removed_group_names.append(name)
            aft = time.time()

            for name in removed_group_names:
                del self.cgroups[name]
            self.delay = aft-bef
            self.hostcpuinfo.update()
            self.cpu_delta = self.hostcpuinfo.get_total_usage_delta()
            now = time.time()
            self.time_delta = now - self.last_time
            self.last_time = now

            self.refresh_display()
            if self.options.iterations is not None:
                iterations += 1
                if iterations >= self.options.iterations:
                    break
            elif iterations == 0:
                iterations = 1

            try:
                events = poll.poll(self.options.delay_seconds * 1000.0)
            except select.error, e:
                if e.args and e.args[0] == errno.EINTR:
                    events = 0
                else:
                    raise
            if not self.options.batch:
                self.resize()
            if events:
                key = self.win.getch()
                self.handle_key(key)

    def get_cgroup_stats(self):
        cgroup_stats = []
        for name, cgroup_list in self.cgroups.iteritems():
            cpu = mem = bio = None
            proc_exists = False
            for _cgroup in cgroup_list:
                subsys_name = cgroup.subsystem_class2name[_cgroup.subsystem.__class__]
                if subsys_name == 'cpu':
                    cpu = _cgroup
                elif subsys_name == 'memory':
                    mem = _cgroup
                elif subsys_name == 'blkio':
                    bio = _cgroup
                else: pass
                if _cgroup.n_procs > 0:
                    proc_exists = True
            if self.hide_empty and not proc_exists:
                continue
            
            active = False
            stats = {}
            stats['name'] = _cgroup.fullname
            stats['n_procs'] = _cgroup.n_procs
            stats['cpu.user'] = 0.0
            stats['cpu.system'] = 0.0
            stats['bio.read']  = 0.0
            stats['bio.write'] = 0.0
            stats['mem.total'] = 0
            stats['mem.rss']   = 0
            stats['mem.swap']  = 0

            if cpu is not None:
                if self.cpu_delta != 0:
                    stats['cpu.user'] = float(cpu.usages_delta['user'])*100/self.cpu_delta
                    stats['cpu.system'] = float(cpu.usages_delta['system'])*100/self.cpu_delta
                if stats['cpu.user'] > 0.0 or stats['cpu.system'] > 0.0:
                    active = True

            if bio is not None:
                bio_stats = bio.usages_delta
                stats['bio.read']  = float(bio_stats['read'])/self.time_delta
                stats['bio.write'] = float(bio_stats['write'])/self.time_delta
                if stats['bio.read'] > 0.0 or stats['bio.write'] > 0.0:
                    active = True

            if mem is not None:
                mem_stats = mem.usages_delta
                stats['mem.total'] = mem_stats['total']
                stats['mem.rss']   = mem_stats['rss']
                stats['mem.swap']  = mem_stats['swap']
                if stats['mem.swap'] != 0 or stats['mem.rss'] != 0 or \
                   stats['mem.swap'] != 0:
                    active = True
            if self.hide_inactive and not active:
                pass
            else:
                cgroup_stats.append(stats)
        cgroup_stats.sort(key=lambda st: st[self.sorting_key],
                          reverse=self.sorting_reverse)
        return cgroup_stats

    def _init_display_params(self):
        self.SUBSYS = ['cpu', 'blkio', 'memory', 'n_procs', 'name']
        subsys_sep_size = 2
        self.SUBSYS_SEP = ' '*subsys_sep_size
        item_sep_size   = 1
        self.ITEM_SEP   = ' '*item_sep_size
        self.ITEM_WIDTHS = {
            'cpu':       formatter.max_width_cpu,
            'blkio':     formatter.max_width_blkio,
            'memory':    formatter.max_width_memory,
            'cpu.user':  formatter.max_width_cpu,
            'cpu.system':formatter.max_width_cpu,
            'bio.read':  formatter.max_width_blkio,
            'bio.write': formatter.max_width_blkio,
            'mem.total': formatter.max_width_memory,
            'mem.rss':   formatter.max_width_memory,
            'mem.swap':  formatter.max_width_memory,
            'n_procs':   3,
            'name':      0}
        self.N_ITEMS = {'cpu': 2, 'blkio': 2,
                        'memory': 3, 'n_procs': 1, 'name': 1}

    def _init_subsys_title(self):
        title_list = []
        for name in self.SUBSYS[:-2]:
            width = self.ITEM_WIDTHS[name]*self.N_ITEMS[name]+self.N_ITEMS[name]-1
            title = '[' + name.upper().center(width-2) + ']'
            title_list.append(title)
        self.SUBSYS_TITLE = self.SUBSYS_SEP.join(title_list)

    def _init_item_titles(self):
        w = self.ITEM_WIDTHS
        self.ITEM_TITLES = [
            'USR'.center(w['cpu.user']),
            self.ITEM_SEP,
            'SYS'.center(w['cpu.system']),
            self.SUBSYS_SEP,
            'READ'.center(w['bio.read']),
            self.ITEM_SEP,
            'WRITE'.center(w['bio.write']),
            self.SUBSYS_SEP,
            'TOTAL'.center(w['mem.total']),
            self.ITEM_SEP,
            'RSS'.center(w['mem.rss']),
            self.ITEM_SEP,
            'SWAP'.center(w['mem.swap']),
            self.SUBSYS_SEP,
            '#'.rjust(w['n_procs']),
            self.ITEM_SEP,
            'NAME'.rjust(w['name']),
            ]
        self.TITLE_KEYS = {
            'cpu.user':0,
            'cpu.system':2,
            'bio.read':4,
            'bio.write':6,
            'mem.total':8,
            'mem.rss':10,
            'mem.swap':12,
            'n_procs':14,
            'name':16,
        }

    def refresh_display(self):
        debug_msg = "%.1f msec elapsed to collect cgroups statistics"%(self.delay*1000,)
        def format(stats):
            w = self.ITEM_WIDTHS
            sep = self.ITEM_SEP
            strs = []

            item2formatters = {
                'cpu.user':  formatter.percent2str,
                'cpu.system':formatter.percent2str,
                'bio.read':  formatter.byps2str,
                'bio.write': formatter.byps2str,
                'mem.total': formatter.byte2str,
                'mem.rss':   formatter.byte2str,
                'mem.swap':  formatter.byte2str,
            }

            def to_s(name):
                if self.hide_zero and stats[name] == 0:
                    return ' '.rjust(w[name])
                else:
                    return item2formatters[name](stats[name]).rjust(w[name])
            strs.append(sep.join([
                to_s('cpu.user'),
                to_s('cpu.system'),
                ]))
            strs.append(sep.join([
                to_s('bio.read'),
                to_s('bio.write'),
                ]))
            strs.append(sep.join([
                to_s('mem.total'),
                to_s('mem.rss'),
                to_s('mem.swap'),
                ]))
            strs.append(sep.join([
                str(stats['n_procs']).rjust(w['n_procs']),
                stats['name']]
                ))
            return self.SUBSYS_SEP.join(strs)

        cgroup_stats = self.get_cgroup_stats()
        lines = map(format, cgroup_stats)

        if self.options.batch:
            print debug_msg
            print self.SUBSYS_TITLE
            print ''.join(self.ITEM_TITLES)
            for l in lines:
                print l
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
        remaining_cols = self.width
        status_msg = ''
        for i in xrange(len(self.ITEM_TITLES)):
            attr = curses.A_REVERSE
            title = self.ITEM_TITLES[i]
            if i == self.TITLE_KEYS[self.sorting_key]:
                attr |= curses.A_BOLD
            title = title[:remaining_cols]
            remaining_cols -= len(title)
            self.win.addstr(title, attr)
        num_lines = min(len(lines), self.height - n_lines - int(bool(status_msg)))
        for i in xrange(num_lines):
            try:
                self.win.insstr(i + n_lines, 0, lines[i].encode('utf-8'))
            except curses.error:
                exc_type, value, traceback = sys.exc_info()
                value = '%s win:%s i:%d line:%s' % \
                        (value, self.win.getmaxyx(), i, lines[i])
                value = str(value).encode('string_escape')
                raise exc_type, value, traceback
        if status_msg:
            self.win.insstr(self.height - 1, 0, status_msg, curses.A_BOLD)
        self.win.refresh()

def run_cgtop_window(win, options):
    def collect_cgroups_by_name(_cgroup, _cgroups):
        if _cgroup.name not in _cgroups:
            _cgroups[_cgroup.name] = []
        _cgroups[_cgroup.name].append(_cgroup)
    
    cgroups = {}
    SUBSYSTEMS = ['cpu', 'memory', 'blkio']
    for subsys_name in SUBSYSTEMS:
        mount_point = cgroup.subsystem2path[subsys_name]
        root_cgroup = cgroup.scan_directory_recursively(subsys_name, mount_point, mount_point)
        cgroup.walk_cgroups(root_cgroup, collect_cgroups_by_name, cgroups)

    ui = CGTopUI(win, cgroups, options)
    ui.run()

def run_cgtop(options):
    if options.batch:
        return run_cgtop_window(None, options)
    else:
        return curses.wrapper(run_cgtop_window, options)

USAGE=''
VERSION='0.1'
def main():
    locale.setlocale(locale.LC_ALL, '')
    parser = optparse.OptionParser(usage=USAGE, version='cgtop ' + VERSION)
    parser.add_option('-i', '--hide-inactive', action='store_true',
                      dest='hide_inactive', default=False,
                      help='Hide inactive groups')
    parser.add_option('-z', '--hide-zero', action='store_true',
                      dest='hide_zero', default=False,
                      help='Hide zero numbers')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups')
    parser.add_option('-b', '--batch', action='store_true', dest='batch',
                      help='non-interactive mode')
    parser.add_option('-n', '--iter', type='int', dest='iterations',
                      metavar='NUM',
                      help='number of iterations before ending [infinite]')
    parser.add_option('-d', '--delay', type='float', dest='delay_seconds',
                      help='delay between iterations [1 second]',
                      metavar='SEC', default=1)
    parser.add_option('--debug', action='store_true', dest='debug',
                      default=False, help='Show debug messages')

    options, args = parser.parse_args()
    if args:
        parser.error('Unexpected arguments: ' + ' '.join(args))

    run_cgtop(options)

if __name__ == "__main__":
    main()
