# What is cgroup-utils?

cgroup-utils provides utility tools and libraries for control groups of Linux.
For example, cgutil top is a top-like tool which shows activities of running processes in control groups.

# Installation

## For users

    $ sudo pip install cgroup-utils

## For developers

    $ git clone git://github.com/peo3/cgroup-utils.git
    $ cd cgroup-utils
    $ python setup.py build
    $ sudo python setup.py install

### Packaging (rpm)

    $ python setup.py bdist --formats=rpm

# Available commands

- configs
- event
- mkdir
- pgrep
- rmdir
- stats
- top
- tree

## cgutil configs

This command show you configurations of cgroups.
By default, it shows only changed configurations.

### Example output

    $ cgutil configs -o memory
    <root>
        notify_on_release=1
    	release_agent=/usr/lib/ulatencyd/ulatencyd_cleanup.lua
    sys_essential
    	swappiness=0
    	notify_on_release=1
    sys_bg
    	swappiness=100
    	notify_on_release=1

## cgutil event

This command makes cgroup.event\_control easy to use.
It exits when a state of a target cgroup crosses a threshold which you set,
thus, you can know the state of the cgroup has changed.

### Example output

    $ cgutil event /sys/fs/cgroup/memory/system/sshd.service/memory.usage_in_bytes +1M
    $ # It exits when memory usage of processes in the cgroup has increased one more MB.

## cgutil pgrep

This command is alike `pgrep` command but it shows cgroups in addtion to PIDs.

### Example output

    $ cgutil pgrep ssh
    /: 15072
    /: 15074
    /system/sshd.service: 630
    $ cgutil pgrep ssh -l -f
    /: 15072 sshd: ozaki-r [priv]
    /: 15074 sshd: ozaki-r@pts/2
    /: 15157 /bin/python /bin/cgutil pgrep ssh -l -f
    /system/sshd.service: 630 /usr/sbin/sshd -D

## cgutil stats

This command shows you states of cgroups.

### Example output

    $ cgutil stats
    <root>
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system  
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/sm-client.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/sendmail.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/vboxadd-service.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/colord.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/colord-sane.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/udisks2.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}
    system/cups.service
            stat={'throttled_time': 0L, 'nr_periods': 0L, 'nr_throttled': 0L}

## cgutil top

This command is alike `top` command but it shows activities in a unit of cgroups.

### Example output

    $ cgutil top -i -n 2 -b
    18.1 msec to collect statistics
    [  CPUACCT  ]  [     BLKIO     ]  [        MEMORY       ]
     USR    SYS      READ    WRITE     TOTAL    RSS     SWAP     # NAME
      0.0%   0.0%    0.0 /s   0.0 /s     0.0    48.0k    0.0    97 usr_1000/default
    20.5 msec to collect statistics
    [  CPUACCT  ]  [     BLKIO     ]  [        MEMORY       ]
     USR    SYS      READ    WRITE     TOTAL    RSS     SWAP     # NAME
      0.0%   0.0%    0.0 /s   0.0 /s   128.0k    4.0k    0.0   104 sys_daemon
      0.0%   0.0%    0.0 /s   0.0 /s   -64.0k    0.0     0.0     0 sys_essential
      0.0%   0.0%    0.0 /s   0.0 /s   108.0k   32.0k    0.0    97 usr_1000/default

## cgutil tree

This command shows you tree structure of cgroups.

### Example outputs
    $ cgutil tree -o blkio
    <root>
       `system
           +sm-client.service
           +sendmail.service
           +vboxadd-service.service
           +colord.service
           +colord-sane.service
           +udisks2.service
           +cups.service
           +rtkit-daemon.service

    (snip)

           +fsck@.service
           +udev.service
           `systemd-journald.service

# Supported Linux Version

4.20.y

## Supported subsystems

- blkio (and its debug feature)
- cpuset
- cpu and cpuacct
- devices
- freezer
- hugetlb
- memory
- net\_cls
- net\_prio
- pids
- rdma

# Supported Python

- python2: 2.6 and above
  - deprecated
- python3: 3.4 and above
  - 3.0 to 3.3 may work but not tested

# License

The tools are distributed under GPLv2. See COPYING for more detail.
