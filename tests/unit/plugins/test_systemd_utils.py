import io
import os
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
    proxy = SimpleNamespace(Locale=["LANG=en_US.UTF-8", "LC_TIME=de_DE.UTF-8", "LANGUAGE=en:de"])
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


# a distribution can build systemd with any version tag, so the property need not start with the version number
@pytest.mark.parametrize("proxy", [SimpleNamespace(Version=""), SimpleNamespace(Version="v252")])
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
    "text,version,expected",
    [
        # systemd 239 and 240 drop the backslash before any character in quotes, also in single quotes
        ('KEY="a\\$b\\x\\"c"', 239, 'a$bx"c'),
        ('KEY="a\\$b\\x\\"c"', 240, 'a$bx"c'),
        ("KEY='a\\'b'", 239, "a'b"),
        ("KEY='a\\'b'", 240, "a'b"),
        ('KEY="cr\\\rx"', 240, "crx"),
        # systemd 241 to 246 keep it except before a double quote, and drop an escaped carriage return
        ('KEY="a\\$b\\x\\"c"', 241, 'a\\$b\\x"c'),
        ('KEY="a\\$b\\x\\"c"', 246, 'a\\$b\\x"c'),
        ("KEY='a\\b'", 241, "a\\b"),
        ('KEY="cr\\\rx"', 246, "crx"),
        # systemd 247 and later drop it only before a character that needs escaping, and keep an escaped return
        ('KEY="a\\$b\\x\\"c"', 247, 'a$b\\x"c'),
        ("KEY='a\\b'", 247, "a\\b"),
        ('KEY="cr\\\rx"', 247, "cr\\\rx"),
    ],
)
def test_parse_env_file_quotes_follow_version(text, version, expected):
    assert systemd.parse_env_file(text, version)[0]["KEY"] == expected


@pytest.mark.parametrize(
    "version,entries,error",
    [
        # systemd 239 parses a file up to its first NUL byte, as the end of the text
        (239, {"KEYMAP": "us", "FONT": "ca"}, None),
        (240, {}, "contains a NUL byte"),
        (262, {}, "contains a NUL byte"),
    ],
)
def test_load_env_file_nul_follows_version(version, entries, error):
    assert systemd.load_env_file(b"KEYMAP=us\nFONT=ca\x00f\nXKBLAYOUT=de\n", version) == (entries, error)


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


def read_all(content, version, reader=None, block=None):
    """Return the lines reader yields for content, read in blocks of block bytes when given."""
    reader = reader or systemd.read_lines
    handle = io.BytesIO(content)

    if block is not None:
        source = handle
        handle = SimpleNamespace(read=lambda size=-1: source.read(min(size, block)))

    return list(reader(handle, version))


@pytest.mark.parametrize(
    "content,lines",
    [
        (b"", []),
        (b"a", ["a"]),
        (b"a\n", ["a"]),
        (b"a\n\n", ["a", ""]),
        # read_line_full() reads a line feed, a carriage return and a NUL, each at most once and a NUL last, as one end
        (b"a\r\nb", ["a", "b"]),
        (b"a\n\rb", ["a", "b"]),
        (b"a\r\0b", ["a", "b"]),
        (b"a\n\r\0b", ["a", "b"]),
        (b"a\r\n\0b", ["a", "b"]),
        (b"a\r\rb", ["a", "", "b"]),
        (b"a\r\n\rb", ["a", "", "b"]),
        (b"a\0\nb", ["a", "", "b"]),
        (b"a\0\0", ["a", ""]),
        (b"a\r\n", ["a"]),
        (b"caf\xe9\n", ["caf\udce9"]),
    ],
)
@pytest.mark.parametrize("block", [None, 1, 2])
def test_read_lines_ends_lines_as_read_line_full(content, lines, block):
    assert read_all(content, 240, block=block) == lines


@pytest.mark.parametrize(
    "content,lines",
    [
        (b"a\r\nb", ["a\r", "b"]),
        (b"a\rb\0c\n", ["a\rb", "c"]),
        (b"a\n\n", ["a", ""]),
        (b"a\0\n", ["a", ""]),
    ],
)
@pytest.mark.parametrize("block", [None, 1])
def test_read_lines_239_ends_lines_at_line_feed_or_nul(content, lines, block):
    assert read_all(content, 239, block=block) == lines


@pytest.mark.parametrize("version", [239, 240])
def test_read_lines_refuses_long_line(version):
    long_line = b"x" * systemd.LONG_LINE_MAX
    assert read_all(b"a\n" + long_line + b"\nb\n", version) == ["a", None]
    assert read_all(b"a\n" + long_line, version) == ["a", None]
    assert read_all(b"a\n" + long_line[1:] + b"\nb", version) == ["a", long_line[1:].decode(), "b"]


@pytest.mark.parametrize(
    "content,lines",
    [
        (b"a\rb\n", ["a\rb\n"]),
        (b"a\0b\nc", ["a", "c"]),
        (b"x" * 2047 + b"y\n", ["x" * 2047, "y\n"]),
        (b"x" * 2046 + b"\n", ["x" * 2046 + "\n"]),
        (b"x" * 5000, ["x" * 2047, "x" * 2047, "x" * 906]),
    ],
)
@pytest.mark.parametrize("block", [None, 100])
def test_read_map_lines_239_reads_as_fgets(content, lines, block):
    assert read_all(content, 239, systemd.read_map_lines, block) == lines


def test_read_map_lines_240_reads_as_read_line():
    assert read_all(b"a\rb\n", 240, systemd.read_map_lines) == ["a", "b"]


@pytest.mark.parametrize(
    "settings,noncharacters,message",
    [
        ([("name", "a\x00b")], True, "invalid name: it must be valid UTF-8 without NUL characters"),
        ([("name", "a\udc80")], False, "invalid name: it must be valid UTF-8 without NUL characters"),
        ([("name", "a\ufdd0")], True, "invalid name: it must not contain Unicode noncharacters"),
        ([("name", "a\U0010ffff")], True, "invalid name: it must not contain Unicode noncharacters"),
    ],
)
def test_check_utf8_refuses(module_factory, invoke, settings, noncharacters, message):
    result = invoke(systemd.check_utf8, module_factory(), settings, noncharacters)
    assert result["failed"] and result["msg"] == message


def test_check_utf8_noncharacters_can_be_left_to_systemd(module_factory):
    module = module_factory()
    systemd.check_utf8(module, [("name", "a\ufdd0\ufffe"), ("other", None), ("empty", "")], noncharacters=False)
    module.fail_json.assert_not_called()


def test_read_bytes_reads_a_missing_file_as_none(module_factory, tmp_path):
    assert systemd.read_bytes(module_factory(), str(tmp_path / "missing")) is None


def test_read_bytes_reads_a_file_that_is_not_regular(module_factory, tmp_path):
    path = tmp_path / "file"
    path.symlink_to("/dev/null")
    assert systemd.read_bytes(module_factory(), str(path)) == b""


def test_read_bytes_reads_a_regular_file(module_factory, tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"KEY=value\n")
    assert systemd.read_bytes(module_factory(), str(path)) == b"KEY=value\n"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_read_bytes_fails_when_the_file_cannot_be_read(module_factory, invoke, tmp_path):
    path = tmp_path / "file"
    path.write_bytes(b"KEY=value\n")
    path.chmod(0)
    result = invoke(systemd.read_bytes, module_factory(), str(path))
    assert result["failed"] and result["msg"].startswith(f"unable to read {path}: ")
