#What is cgroup-utils?

cgroup-utils provides utility tools and libraries for control groups of Linux.
For example, cgtop is a top-like tool which shows activities of running processes based on the POV of control groups.


#Installation

    $ python setup.py build
    $ sudo python setup.py install

#Available tools
- cgutil configs
- cgutil pgrep
- cgutil stats
- cgutil top
- cgutil tree
- cgroup_event_listener

#Example outputs

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
    usr_1000
    	notify_on_release=1
    usr_1000/active
    	swappiness=0
    	notify_on_release=1
    usr_1000/ui
    	swappiness=0
    	notify_on_release=1
    usr_1000/default
    	notify_on_release=1
    sys_daemon
    	swappiness=70
    	notify_on_release=1

#Supported Linux Version

3.4.y

#License

The tools are distributed under GPLv2. See COPYING for more detail.
