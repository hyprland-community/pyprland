from pyprland.models import VersionInfo


def test_version_info_init():
    v = VersionInfo(1, 2, 3)
    assert v.major == 1
    assert v.minor == 2
    assert v.micro == 3


def test_version_info_defaults():
    v = VersionInfo()
    assert v.major == 0
    assert v.minor == 0
    assert v.micro == 0


def test_version_info_compare_major():
    v1 = VersionInfo(1, 0, 0)
    v2 = VersionInfo(0, 9, 9)
    assert v1 > v2
    assert v2 < v1


def test_version_info_compare_minor():
    v1 = VersionInfo(0, 10, 0)
    v2 = VersionInfo(0, 9, 9)
    assert v1 > v2
    assert v2 < v1


def test_version_info_compare_micro():
    v1 = VersionInfo(0, 0, 2)
    v2 = VersionInfo(0, 0, 1)
    assert v1 > v2
    assert v2 < v1


def test_version_info_equality():
    v1 = VersionInfo(1, 2, 3)
    v2 = VersionInfo(1, 2, 3)
    v3 = VersionInfo(1, 2, 4)
    assert v1 == v2
    assert v1 != v3
