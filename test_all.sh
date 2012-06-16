#!/bin/sh

SUBSYS="cpu cpuacct cpuset memory blkio freezer net_cls devices"
ERRFILE=/tmp/.cgroup-utils.stderr

enabled_cgroups=
while read name _ _ enabled; do
    if [ $enabled = 1 ]; then
        if [ $name != perf_event ]; then
            enabled_cgroups="$enabled_cgroups $name"
        fi
    fi
done < /proc/cgroups

test_one()
{
    $* >/dev/null 2>$ERRFILE
	ret=$?
    if [ $ret != 0 ]; then
        grep -q "EnvironmentError: Not enabled in the system" $ERRFILE
        if [ $? = 0 ]; then
            echo "[??] $*"
        else
            echo "[NG] $*"
            cat $ERRFILE
        fi
	else
        echo "[ok] $*"
	fi
}

export PYTHONPATH=.

for subsys in $enabled_cgroups; do
    test_one python bin/cgtree -o $subsys
    test_one python bin/cgshowconfigs -o $subsys
    test_one python bin/cgshowstats -o $subsys
done
test_one python bin/cgtop -b -n 1
