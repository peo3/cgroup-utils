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

test_run()
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

test_support()
{
    $* >/dev/null 2>$ERRFILE
    ret=$?
    if [ $ret != 0 ]; then
        echo "[NG] $*"
        cat $ERRFILE
    else
        echo "[ok] $*"
    fi
}

export PYTHONPATH=.

echo "## Testing each subcommands for each subsystems"
for subsys in $enabled_cgroups; do
    test_run python bin/cgutil tree -o $subsys
    test_run python bin/cgutil configs -o $subsys
    test_run python bin/cgutil stats -o $subsys
done
test_run python bin/cgutil top -b -n 1

echo "## Checking unsupported files of subsystems"
for subsys in $enabled_cgroups; do
    test_support python bin/check_support -o $subsys
done
