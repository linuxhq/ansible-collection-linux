from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ansible_collections.linuxhq.linux.plugins.module_utils import systemd


@pytest.mark.parametrize(
    "value,expected",
    [
        (b"\x00\xff", "00ff"),
        (bytearray(b"\x01"), "01"),
        ([0, 255], "00ff"),
        ([True, False], [True, False]),
        ([], []),
        ([256], [256]),
        (["x"], ["x"]),
        ("text", "text"),
        (None, None),
    ],
)
def test_property_conversion(value, expected):
    assert systemd.systemd_value(value) == expected


def test_missing_property_is_none(module_factory):
    proxy = SimpleNamespace(BootID=b"\x00\xff")
    assert systemd.systemd_properties(module_factory(), proxy, [("boot_id", "BootID"), ("missing", "Missing")]) == {
        "boot_id": "00ff",
        "missing": None,
    }


def test_property_bus_error(module_factory, invoke):
    class BrokenProxy:
        @property
        def Hostname(self):
            raise systemd.DBusError("denied")

    result = invoke(systemd.systemd_properties, module_factory(), BrokenProxy(), [("hostname", "Hostname")])
    assert result["failed"] and "Hostname" in result["msg"]


@pytest.mark.parametrize("error", [systemd.GLibError("Timeout was reached"), TimeoutError("timed out")])
def test_property_transport_error(module_factory, invoke, error):
    class BrokenProxy:
        @property
        def NTP(self):
            raise error

    result = invoke(systemd.systemd_properties, module_factory(), BrokenProxy(), [("ntp", "NTP")])
    assert result["failed"] and result["msg"] == f"unable to read the NTP property: {error}"


@pytest.mark.parametrize("error", [systemd.GLibError("Timeout was reached"), TimeoutError("timed out")])
def test_method_transport_error(module_factory, invoke, error):
    proxy = SimpleNamespace(SetNTP=Mock(side_effect=error))
    result = invoke(systemd.systemd_call, module_factory(), proxy, "SetNTP", False, False)
    assert result["failed"] and result["msg"] == f"unable to call SetNTP: {error}"


def test_method_missing_and_bus_error(module_factory, invoke):
    result = invoke(systemd.systemd_result, module_factory(), SimpleNamespace(), "SetHostname", "host")
    assert result["failed"] and "not supported" in result["msg"]
    proxy = SimpleNamespace(SetHostname=Mock(side_effect=systemd.DBusError("denied")))
    result = invoke(systemd.systemd_call, module_factory(), proxy, "SetHostname", "host", False)
    assert result["failed"] and "denied" in result["msg"]


def test_system_bus_connection(monkeypatch, module_factory):
    bus = Mock()
    constructor = Mock(return_value=bus)
    monkeypatch.setattr(systemd, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd, "SystemMessageBus", constructor, raising=False)
    assert systemd.systemd_proxy(module_factory(), "hostname1") is bus.get_proxy.return_value
    bus.get_proxy.assert_called_once_with("org.freedesktop.hostname1", "/org/freedesktop/hostname1")


def test_unreachable_system_bus(monkeypatch, module_factory, invoke):
    class LazyBus:
        @property
        def connection(self):
            raise systemd.GLibError("Could not connect: No such file or directory")

        def get_proxy(self, *args):
            return Mock()

    monkeypatch.setattr(systemd, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd, "SystemMessageBus", LazyBus, raising=False)
    result = invoke(systemd.systemd_proxy, module_factory(), "hostname1")
    assert result["failed"]
    assert result["msg"] == (
        "unable to reach org.freedesktop.hostname1 on the system bus: Could not connect: No such file or directory"
    )


def test_missing_dasbus(monkeypatch, module_factory, invoke):
    monkeypatch.setattr(systemd, "HAS_DASBUS", False)
    result = invoke(systemd.systemd_proxy, module_factory(), "hostname1")
    assert result["failed"] and "dasbus" in result["msg"]


def test_locale_normalization_and_preservation(module_factory):
    proxy = SimpleNamespace(Locale=["LANG=en_US.UTF-8", "LC_TIME=de_DE.UTF-8", "LANGUAGE=en:de", "malformed"])
    result = systemd.locale_status(module_factory(), proxy)
    assert result["locale"]["lang"] == "en_US.UTF-8"
    assert result["locale"]["lc_time"] == "de_DE.UTF-8"
    assert result["locale"]["lc_numeric"] is None
    variables = {"lang": "en_US.UTF-8", "lc_time": "en_US.UTF-8", "lc_numeric": "de_DE.UTF-8", "lc_name": None}
    assert systemd.locale_simplify(variables) == {"lang": "en_US.UTF-8", "lc_numeric": "de_DE.UTF-8"}
    assert systemd.locale_setting({"lc_time": "de_DE.UTF-8", "lang": "en_US.UTF-8"}) == [
        "LANG=en_US.UTF-8",
        "LC_TIME=de_DE.UTF-8",
    ]
    assert variables["lc_time"] == "en_US.UTF-8"


@pytest.mark.parametrize(
    "version,expected",
    [("252-51.el9_6.2.alma.2", 252), ("252.39-1~deb12u1", 252), ("257.8-1~deb13u2", 257), ("262", 262)],
)
def test_systemd_version(monkeypatch, module_factory, version, expected):
    proxy = SimpleNamespace(Version=version)
    monkeypatch.setattr(systemd, "systemd_proxy", Mock(return_value=proxy))
    assert systemd.systemd_version(module_factory()) == expected
    assert systemd.systemd_proxy.call_args.args[1] == "systemd1"


@pytest.mark.parametrize("proxy", [SimpleNamespace(), SimpleNamespace(Version=""), SimpleNamespace(Version="v252")])
def test_systemd_version_unreadable(monkeypatch, module_factory, invoke, proxy):
    monkeypatch.setattr(systemd, "systemd_proxy", Mock(return_value=proxy))
    result = invoke(systemd.systemd_version, module_factory())
    assert result["failed"] and "unable to read the systemd version" in result["msg"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("KEY=plain", "plain"),
        ("KEY=  padded value  ", "padded value"),
        ('KEY="quoted value "', "quoted value "),
        ("KEY='single \\ quoted'", "single \\ quoted"),
        ('KEY="a\\$b\\x"', "a$b\\x"),
        ("KEY=escaped\\ space", "escaped space"),
        ("KEY=", ""),
        ("KEY=Taylor's Laptop", "Taylor's Laptop"),
        ('KEY=a"b c"', 'a"b c"'),
        ('KEY="a" "b"', "ab"),
        ("KEY='a' b  ", "ab"),
        ("KEY=nbsp\u00a0", "nbsp\u00a0"),
        ("KEY=tab\t \n", "tab"),
        ("KEY=con\\\ntinued", "continued"),
        ('KEY="con\\\ntinued"', "continued"),
        ("KEY='multi\nline'", "multi\nline"),
        ("KEY=crlf\r\nOTHER=x", "crlf"),
        ("KEY=cr\rOTHER=x", "cr"),
        ("  KEY  =spaced key", "spaced key"),
        ("KEY=first\nKEY=second\n", "second"),
        ("# KEY=comment\n; KEY=comment\nKEY=value", "value"),
        ("# comment ending in a backslash \\\nKEY=value", "value"),
        ("NOKEY\nKEY=value", "value"),
    ],
)
def test_parse_env_file(text, expected):
    assert systemd.parse_env_file(text, 262)[0].get("KEY", "") == expected


@pytest.mark.parametrize(
    "text,loadable",
    [
        ("KEY=value\n# caf\udce9\nJUNK\udce9\n", True),
        ("KEY=caf\udce9\nOTHER=x\n", False),
        ("K\udce9Y=1\n", False),
        ("KEY=\ufdd0\n", False),
        ("KEY=value\nOTHER=\udcff", False),
        ("KEY='\udcff", False),
    ],
)
def test_parse_env_file_reports_whether_systemd_loads_it(text, loadable):
    assert systemd.parse_env_file(text, 262)[1] is loadable


@pytest.mark.parametrize("version,expected", [(252, ""), (253, ""), (254, "Foo"), (257, "Foo"), (262, "Foo")])
def test_parse_env_file_escaped_comment_follows_version(version, expected):
    text = "# note \\\nPRETTY_HOSTNAME=Foo\n"
    assert systemd.parse_env_file(text, version)[0].get("PRETTY_HOSTNAME", "") == expected


@pytest.mark.parametrize(
    "content,error",
    [
        (b"", None),
        (b"KEYMAP=us\nFONT=eurlatgr\n", None),
        (b"KEYMAP=us\n# caf\xe9\n", None),
        (b"KEYMAP=us\nFONT=caf\xe9\n", "contains a setting that is not valid UTF-8"),
        (b"KEYMAP=us\nFONT=ca\x00f\n", "contains a NUL byte"),
    ],
)
def test_load_env_file_reports_why_systemd_refuses_it(content, error):
    assert systemd.load_env_file(content, 262)[1] == error


def test_load_env_file_keeps_entries_before_an_invalid_one():
    assert systemd.load_env_file(b"KEYMAP=us\nFONT=caf\xe9\nKEYMAP_TOGGLE=de\n", 262)[0] == {"KEYMAP": "us"}
