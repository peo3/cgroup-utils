#!/bin/sh

SUBSYS="cpu cpuacct cpuset memory blkio freezer net_cls devices"
ERRFILE=/tmp/.cgroup-utils.stderr

test_one()
{
        $* >/dev/null 2>$ERRFILE
	ret=$?
        if [ $ret != 0 -a $ret != 3 ]; then
                echo "[NG] $*"
                cat $ERRFILE
        elif [ $ret = 3 ]; then
                echo "[??] $*"
	else
                echo "[ok] $*"
	fi
}

for subsys in $SUBSYS; do
        test_one cgtree -o $subsys
        test_one cgshowconfigs -o $subsys
done
test_one cgtop -b -n 1
