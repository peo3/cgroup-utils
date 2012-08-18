#!/bin/sh

SUBSYS="cpu cpuacct cpuset memory blkio freezer net_cls devices"
ERRFILE=/tmp/.cgroup-utils.stderr

enabled_cgroups=
while read name _ _ enabled; do
    if [ $enabled = 1 ]; then
        if [ $name != perf_event -a $name != debug ]; then
            enabled_cgroups="$enabled_cgroups $name"
        fi
    fi
done < /proc/cgroups

named_cgroup=$(grep cgroup /proc/mounts | egrep -o -e 'name=[^,\ ]*')
if [ -n "$named_cgroup" ]; then
    enabled_cgroups="$enabled_cgroups $named_cgroup"
fi

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

test_run_event()
{
    $* >/dev/null 2>$ERRFILE
    ret=$?
    if [ $? = 2 ]; then
        echo "[ok] $*"
    else
        echo "[NG] $*"
        cat $ERRFILE
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

buildpath=$(find ./build/lib.linux* -maxdepth 0 -type d)
export PYTHONPATH=$buildpath:.

echo "## Testing each commands for each subsystems"
for subsys in $enabled_cgroups; do
    test_run python bin/cgutil tree -o $subsys
    test_run python bin/cgutil configs -o $subsys
    test_run python bin/cgutil stats -o $subsys
done
test_run python bin/cgutil top -b -n 1
root=$(awk '/^cgroup.*memory/ {print $2;}' /proc/mounts)
path=$root/memory.usage_in_bytes
test_run python bin/cgutil event -t 0.1 $path +1M
path=$root/memory.oom_control
test_run python bin/cgutil event -t 0.1 $path

echo "## Testing each command helps"
for cmd in configs event pgrep stats top tree; do
    test_run python bin/cgutil $cmd --help
done

echo "## Checking unsupported files of subsystems"
for subsys in $enabled_cgroups; do
    test_support python bin/check_support -o $subsys
done
