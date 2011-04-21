#!/usr/bin/python

import sys
import optparse

import cgroup
import formatter

def print_configs(_cgroup, show_default):
    configs = _cgroup.get_configs()
    defaults = _cgroup.get_default_configs()
    for name, val in configs.iteritems():
        if not show_default and defaults[name] == val:
            continue
        if 'in_bytes' in name:
            if val == defaults[name]:
                print("\t%s="%(name,))
            else:
                print("\t%s=%s"%(name, formatter.byte2str(val)))
        else:
            print("\t%s=%s"%(name, str(val)))

def main():
    DEFAULT_SUBSYSTEM = 'cpu'

    parser = optparse.OptionParser()
    parser.add_option('-o', action='store', type='string',
                      dest='target_subsystem', default=DEFAULT_SUBSYSTEM,
                      help='Specify a subsystem')
    parser.add_option('--show-default', action='store_true',
                      dest='show_default', default=False,
                      help='Show every parameters including default values')
    parser.add_option('-e', '--hide-empty', action='store_true',
                      dest='hide_empty', default=False,
                      help='Hide empty groups')
    parser.add_option('-v', '--verbose', action='store_true',
                      dest='verbose', default=False,
                      help='Show detailed messages')
    parser.add_option('--debug', action='store_true', dest='debug',
                      default=False, help='Show debug messages')
    (options, _args) = parser.parse_args()
    if options.debug:
        print options

    if options.target_subsystem not in cgroup.subsystem2path:
        print('No such subsystem: %s'%(options.target_subsystem,))
        sys.exit(3)

    target_path = cgroup.subsystem2path[options.target_subsystem]
    mount_point = target_path

    root_cgroup = cgroup.scan_directory_recursively(
                      options.target_subsystem,
                      mount_point, mount_point)

    def print_cgroups_recursively(_cgroup):
        if options.debug:
            print(_cgroup)

        if options.hide_empty and _cgroup.n_procs == 0:
            pass
        else:
            print(_cgroup.fullname)
            print_configs(_cgroup, options.show_default)
        for child in _cgroup.childs:
            print_cgroups_recursively(child)
    print_cgroups_recursively(root_cgroup)

if __name__ == "__main__":
    main()
