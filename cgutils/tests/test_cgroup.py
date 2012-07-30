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
    assert cgroup.SimpleStat.parse(input) == {'user': 2978976, 'system': 1037760}

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
