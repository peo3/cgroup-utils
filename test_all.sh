#!/bin/sh

SUBSYS="cpu cpuacct cpuset memory blkio freezer net_cls devices"
ERRFILE=/tmp/.cgroup-utils.stderr

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

for subsys in $SUBSYS; do
        test_one cgtree -o $subsys
        test_one cgshowconfigs -o $subsys
done
test_one cgtop -b -n 1
