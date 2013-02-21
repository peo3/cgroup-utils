from cgutils import cgroup


def test_SimpleList():
    input = '100\n103\n234\n'
    assert cgroup.SimpleList.parse(input) == [100, 103, 234]

    input = '100\n'
    assert cgroup.SimpleList.parse(input) == [100]

    input = ''
    assert cgroup.SimpleList.parse(input) == []


def test_SimpleStat():
    input = 'user 2978976\nsystem 1037760\n'
    assert cgroup.SimpleStat.parse(input) == \
        {'user': 2978976, 'system': 1037760}

    input = ''
    assert cgroup.SimpleStat.parse(input) == {}


def test_BlkioStat():
    input = """8:0 Read 72650752
8:0 Write 28090368
8:0 Sync 28090368
8:0 Async 72650752
8:0 Total 100741120
Total 100741120
"""
    output = {
        'Total': 100741120,
        '8:0': {
            'Read': 72650752,
            'Write': 28090368,
            'Sync': 28090368,
            'Async': 72650752,
            'Total': 100741120,
        }
    }
    assert cgroup.BlkioStat.parse(input) == output

    input = """8:0 Read 72650752
8:0 Write 28090368
8:0 Sync 28090368
8:0 Async 72650752
8:0 Total 100741120
9:0 Read 72650752
9:0 Write 28090368
9:0 Sync 28090368
9:0 Async 72650752
9:0 Total 100741120
Total 201482240
"""

    output = {
        'Total': 201482240,
        '8:0': {
            'Read': 72650752,
            'Write': 28090368,
            'Sync': 28090368,
            'Async': 72650752,
            'Total': 100741120,
        },
        '9:0': {
            'Read': 72650752,
            'Write': 28090368,
            'Sync': 28090368,
            'Async': 72650752,
            'Total': 100741120,
        }
    }
    assert cgroup.BlkioStat.parse(input) == output


def test_DevicesStat():
    input = """a *:* rwm

c 136:* rwm
c 1:3 rwm
"""
    output = [
        'a *:* rwm',
        'c 136:* rwm',
        'c 1:3 rwm',
    ]
    assert cgroup.DevicesStat.parse(input) == output

    input = ''
    assert cgroup.DevicesStat.parse(input) == []


def test_NumaStat():
    input = """total=83920 N0=83920
file=63452 N0=63452
anon=20468 N0=20468
unevictable=0 N0=0
"""
    output = {
        'total': {
            'total': 83920,
            'N0': 83920,
        },
        'file': {
            'total': 63452,
            'N0': 63452,
        },
        'anon': {
            'total': 20468,
            'N0': 20468,
        },
        'unevictable': {
            'total': 0,
            'N0': 0,
        },
    }
    assert cgroup.NumaStat.parse(input) == output


def test_PercpuStat():
    # A line may end with a redundant space
    input = '836842800783 656015556351 '
    assert cgroup.PercpuStat.parse(input) == {0: 836842800783, 1: 656015556351}

    input = '836842800783 '
    assert cgroup.PercpuStat.parse(input) == {0: 836842800783}


def test_SlabinfoStat():
    input = """slabinfo - version: 2.1
# name            <active_objs> <num_objs> <objsize> <objperslab> <pagesperslab> : tunables <limit> <batchcount> <sharedfactor> : slabdata <active_slabs> <num_slabs> <sharedavail>
kmalloc-128           32     32    128   32    1 : tunables    0    0    0 : slabdata      1      1      0
anon_vma              64     64     64   64    1 : tunables    0    0    0 : slabdata      1      1      0
mm_struct             18     18    896   18    4 : tunables    0    0    0 : slabdata      1      1      0
"""

    expected = {
        'kmalloc-128': {
            'active_objs': 32,
            'num_objs': 32,
            'objsize': 128,
            'objperslab': 32,
            'pagesperslab': 1,
            'tunables': {
                'limit': 0,
                'batchcount': 0,
                'sharedfactor': 0,
            },
            'slabdata': {
                'active_slabs': 1,
                'num_slabs': 1,
                'sharedavail': 0,
            },
        },
        'anon_vma': {
            'active_objs': 64,
            'num_objs': 64,
            'objsize': 64,
            'objperslab': 64,
            'pagesperslab': 1,
            'tunables': {
                'limit': 0,
                'batchcount': 0,
                'sharedfactor': 0,
            },
            'slabdata': {
                'active_slabs': 1,
                'num_slabs': 1,
                'sharedavail': 0,
            },
        },
        'mm_struct': {
            'active_objs': 18,
            'num_objs': 18,
            'objsize': 896,
            'objperslab': 18,
            'pagesperslab': 4,
            'tunables': {
                'limit': 0,
                'batchcount': 0,
                'sharedfactor': 0,
            },
            'slabdata': {
                'active_slabs': 1,
                'num_slabs': 1,
                'sharedavail': 0,
            },
        },
    }

    #import pprint
    #pprint.pprint(cgroup.SlabinfoStat.parse(input))
    #pprint.pprint(expected)
    assert cgroup.SlabinfoStat.parse(input) == expected
