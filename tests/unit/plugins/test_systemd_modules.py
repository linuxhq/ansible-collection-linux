import errno
import os
import signal
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import Mock

import pytest

from ansible.module_utils import basic

from ansible_collections.linuxhq.linux.plugins.modules import (
    systemd_hostname,
    systemd_hostname_info,
    systemd_locale,
    systemd_locale_info,
    systemd_timedate,
    systemd_timedate_info,
)

RUN_COMMAND = basic.AnsibleModule.run_command
DEBIAN_FAMILY = systemd_locale.debian_family

HOSTNAME = {
    "default_hostname": "localhost",
    "hostname": "old",
    "hostname_source": "static",
    "static_hostname": "old",
    "pretty_hostname": "Old",
    "chassis": "server",
    "deployment": "prod",
    "icon_name": "computer",
    "location": "rack",
}
LOCALE = {
    "locale": {"lang": "en_US.UTF-8"},
    "vconsole_keymap": "us",
    "vconsole_keymap_toggle": "",
    "x11_layout": "us",
    "x11_model": "pc105",
    "x11_variant": "",
    "x11_options": "",
}
TIMEDATE = {"timezone": "UTC", "local_rtc": False, "ntp": False, "can_ntp": True, "time_usec": 0}
MANAGERS = [
    (
        systemd_hostname,
        "hostname",
        "systemd_properties",
        HOSTNAME,
        {"static_hostname": "new"},
        "SetStaticHostname",
        ("new", False),
    ),
    (
        systemd_locale,
        "locale",
        "locale_status",
        LOCALE,
        {"x11_layout": "de"},
        "SetX11Keyboard",
        ("de", "pc105", "", "", True, False),
    ),
    (
        systemd_timedate,
        "timedate",
        "systemd_properties",
        TIMEDATE,
        {"timezone": "Europe/Berlin"},
        "SetTimezone",
        ("Europe/Berlin", False),
    ),
]


@pytest.fixture(autouse=True)
def hostname_files(monkeypatch, tmp_path):
    """Point the hostname module at files under tmp_path that do not exist until a test writes them."""
    files = {"hostname": tmp_path / "hostname", "machine_info": tmp_path / "machine-info"}
    monkeypatch.setattr(systemd_hostname, "HOSTNAME_FILE", str(files["hostname"]))
    monkeypatch.setattr(systemd_hostname, "MACHINE_INFO", str(files["machine_info"]))
    return files


@pytest.fixture(autouse=True)
def keyboard_files(monkeypatch, tmp_path):
    """Point the locale module at keyboard files and a language fallback map under tmp_path that do not exist until a
    test writes them."""
    files = {
        "vconsole": tmp_path / "vconsole.conf",
        "keyboard": tmp_path / "keyboard",
        "language_fallback_map": tmp_path / "language-fallback-map",
    }
    monkeypatch.setattr(systemd_locale, "VCONSOLE_CONF", str(files["vconsole"]))
    monkeypatch.setattr(systemd_locale, "DEBIAN_KEYBOARD", str(files["keyboard"]))
    monkeypatch.setattr(systemd_locale, "LANGUAGE_FALLBACK_MAP", str(files["language_fallback_map"]))
    monkeypatch.setattr(systemd_locale, "debian_family", Mock(return_value=False))
    return files


class Expired(BaseException):
    """Raised by time_limit, outside Exception so that no handler for OSError, such as TimeoutError, catches it."""


@contextmanager
def time_limit(seconds=5):
    """Fail a read that would block or never end, such as of a FIFO or /dev/zero, instead of hanging the tests."""

    def expire(signum, frame):
        raise Expired(f"still running after {seconds} seconds")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def analyze_output(seconds, original="2026-07-26 14:30"):
    """Return systemd-analyze timestamp output with the given UNIX seconds field, as systemd 252 prints it."""
    return (
        f"  Original form: {original}\n"
        "Normalized form: Sun 2026-07-26 14:30:00 UTC\n"
        f"   UNIX seconds: {seconds}\n"
        "       From now: 1 week 3 days left\n"
    )


@pytest.fixture
def analyze(monkeypatch, run_module):
    """Answer systemd-analyze timestamp through AnsibleModule.run_command, once per call."""
    command = Mock(return_value=(0, analyze_output("@1784083200"), ""))
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", Mock(return_value="/usr/bin/systemd-analyze"))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", command)
    return command


@pytest.fixture(autouse=True)
def systemd_version(monkeypatch):
    """Report systemd 262 to the hostname and locale modules unless a test sets another version."""
    version = Mock(return_value=262)
    monkeypatch.setattr(systemd_hostname, "systemd_version", version)
    monkeypatch.setattr(systemd_locale, "systemd_version", version)
    return version


@pytest.mark.parametrize("plugin,key,reader,current,params,method,args", MANAGERS)
@pytest.mark.parametrize("check_mode", [False, True])
def test_manager_changes_and_check_mode(
    monkeypatch, run_module, plugin, key, reader, current, params, method, args, check_mode
):
    monkeypatch.setattr(plugin, "HAS_DASBUS", True)
    proxy = object()
    monkeypatch.setattr(plugin, "systemd_proxy", lambda *args: proxy)
    initial = deepcopy(current)
    updated = {**current, **params}
    if plugin is systemd_hostname:
        updated["hostname"] = "new"

    read = Mock(side_effect=[initial, updated])
    monkeypatch.setattr(plugin, reader, read)
    mutate = Mock()
    monkeypatch.setattr(plugin, "systemd_call", mutate)
    result = run_module(plugin, params, check_mode)
    assert result["changed"]
    for name, value in params.items():
        assert result[key][name] == value

    assert initial == current
    if check_mode:
        mutate.assert_not_called()
        assert read.call_count == 1
    else:
        assert mutate.call_args.args[1:] == (proxy, method, *args)
        assert read.call_count == 2


@pytest.mark.parametrize("plugin,key,reader,current,params,method,args", MANAGERS)
def test_manager_no_options_is_idempotent(monkeypatch, run_module, plugin, key, reader, current, params, method, args):
    monkeypatch.setattr(plugin, "systemd_proxy", Mock())
    monkeypatch.setattr(plugin, reader, Mock(return_value=deepcopy(current)))
    mutate = Mock(side_effect=AssertionError("must not mutate"))
    monkeypatch.setattr(plugin, "systemd_call", mutate)
    assert run_module(plugin) == {"changed": False, key: current}
    mutate.assert_not_called()


@pytest.mark.parametrize("plugin,key,reader,current,params,method,args", MANAGERS)
def test_manager_missing_dasbus_in_check_mode(
    monkeypatch, run_module, plugin, key, reader, current, params, method, args
):
    monkeypatch.setattr(plugin, "HAS_DASBUS", False)
    proxy = Mock(side_effect=AssertionError("must not contact D-Bus"))
    monkeypatch.setattr(plugin, "systemd_proxy", proxy)
    assert run_module(plugin, params, True) == {"changed": True, key: {}}
    assert run_module(plugin, {}, True) == {"changed": False, key: {}}


@pytest.mark.parametrize(
    "plugin,key,reader,current",
    [
        (systemd_hostname_info, "hostname", "systemd_properties", HOSTNAME),
        (systemd_locale_info, "locale", "locale_status", LOCALE),
        (systemd_timedate_info, "timedate", "systemd_properties", TIMEDATE),
    ],
)
@pytest.mark.parametrize("missing", [False, True])
def test_info_is_read_only(monkeypatch, run_module, plugin, key, reader, current, missing):
    monkeypatch.setattr(plugin, "HAS_DASBUS", not missing)
    proxy = Mock()
    monkeypatch.setattr(plugin, "systemd_proxy", proxy)
    monkeypatch.setattr(plugin, reader, Mock(return_value=current))
    if plugin is systemd_timedate_info:
        monkeypatch.setattr(plugin, "systemd_result", Mock(return_value=("UTC", "Europe/Berlin")))

    result = run_module(plugin, check_mode=True)
    assert result[key] == ({} if missing else current)
    assert not result["changed"]
    if missing:
        proxy.assert_not_called()

    if plugin is systemd_timedate_info:
        assert result["timezones"] == ([] if missing else ["UTC", "Europe/Berlin"])


def test_transient_hostname_cannot_override_static(monkeypatch, run_module):
    monkeypatch.setattr(systemd_hostname, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_hostname, "systemd_properties", Mock(return_value=HOSTNAME))
    mutate = Mock()
    monkeypatch.setattr(systemd_hostname, "systemd_call", mutate)
    result = run_module(systemd_hostname, {"transient_hostname": "transient"})
    assert result["failed"] and "takes precedence" in result["msg"]
    mutate.assert_not_called()


def test_clear_static_before_setting_transient(monkeypatch, run_module, hostname_files):
    hostname_files["hostname"].write_text("old\n")
    monkeypatch.setattr(systemd_hostname, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_hostname, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_hostname, "systemd_properties", Mock(return_value=HOSTNAME))
    result = run_module(systemd_hostname, {"static_hostname": "", "transient_hostname": "transient"}, True)
    assert result["hostname"]["hostname"] == "transient"
    assert result["hostname"]["static_hostname"] == ""


def test_ntp_requires_available_service(monkeypatch, run_module):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "can_ntp": False}))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "ntp": True})
    assert result["failed"] and "no network time service" in result["msg"]
    mutate.assert_not_called()


def test_ntp_alone_is_left_to_systemd(monkeypatch, run_module):
    # SetNTP is the first request, so systemd-timedated refuses it before anything is written
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "can_ntp": False}))
    calls = []

    def refuse(module, proxy, method, *args):
        calls.append(method)
        module.fail_json(msg=f"unable to call {method}: NTP not supported")

    monkeypatch.setattr(systemd_timedate, "systemd_call", refuse)
    result = run_module(systemd_timedate, {"ntp": True})
    assert result["failed"] and result["msg"] == "unable to call SetNTP: NTP not supported"
    assert calls == ["SetNTP"]


def test_locale_change_preserves_unspecified_categories(monkeypatch, run_module):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    status = {**LOCALE, "locale": {"lang": "en_US.UTF-8", "lc_numeric": "de_DE.UTF-8"}}
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=status))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": {"lc_time": "fr_FR.UTF-8"}}, True)
    assert result["changed"]
    assert result["locale"]["locale"]["lang"] == "en_US.UTF-8"
    assert result["locale"]["locale"]["lc_numeric"] == "de_DE.UTF-8"
    assert result["locale"]["locale"]["lc_time"] == "fr_FR.UTF-8"
    mutate.assert_not_called()


def test_locale_applies_sorted_settings(monkeypatch, run_module):
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    params = {"locale": {"lc_time": "fr_FR.UTF-8", "lc_numeric": "de_DE.UTF-8", "lc_name": ""}}
    assert run_module(systemd_locale, params)["changed"]
    assert mutate.call_args.args[2:] == ("SetLocale", ["LC_NUMERIC=de_DE.UTF-8", "LC_TIME=fr_FR.UTF-8"], False)


@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_sends_only_requested_variables(monkeypatch, run_module, check_mode):
    configured = {**LOCALE, "locale": {"lang": "en_US.UTF-8", "language": "en_US:en"}}
    updated = {**LOCALE, "locale": {**configured["locale"], "lc_time": "en_GB.UTF-8"}}
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(side_effect=[configured, updated]))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": {"lc_time": "en_GB.UTF-8"}}, check_mode)
    assert result["changed"]
    assert result["locale"]["locale"]["lang"] == "en_US.UTF-8"
    assert result["locale"]["locale"]["language"] == "en_US:en"
    assert result["locale"]["locale"]["lc_time"] == "en_GB.UTF-8"
    if check_mode:
        mutate.assert_not_called()
    else:
        assert mutate.call_args.args[2:] == ("SetLocale", ["LC_TIME=en_GB.UTF-8"], False)


@pytest.mark.parametrize(
    "configured,params,expected",
    [
        # localed derives LANGUAGE from a sent LANG, so an unchanged LANG is not sent
        ({"lang": "en_AU", "language": "en_US"}, {"lang": "en_AU", "lc_time": "C.UTF-8"}, ["LC_TIME=C.UTF-8"]),
        # localed drops LC_TIME equal to the merged LANG, so the change converges without sending LANG
        ({"lang": "en_AU", "lc_time": "C.UTF-8"}, {"lang": "en_AU", "lc_time": "en_AU"}, ["LC_TIME=en_AU"]),
        # a requested LANGUAGE is sent with a changed LANG so the fallback map does not replace it
        (
            {"lang": "en_US", "language": "en_US"},
            {"lang": "en_AU", "language": "en_US"},
            ["LANG=en_AU", "LANGUAGE=en_US"],
        ),
        # without a requested LANGUAGE, a changed LANG is sent alone, so localed applies its fallback map
        ({"lang": "en_US", "language": "en_US"}, {"lang": "en_AU"}, ["LANG=en_AU"]),
    ],
)
def test_locale_sends_only_changed_variables(monkeypatch, run_module, configured, params, expected):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value={**LOCALE, "locale": configured}))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    assert run_module(systemd_locale, {"locale": params})["changed"]
    assert mutate.call_args.args[2:] == ("SetLocale", expected, False)


# a map based on the one systemd ships, with the line ends, comments and malformed lines find_language_fallback()
# skips, and an entry whose fallback equals its LANG
LANGUAGE_FALLBACK_MAP = (
    "# comment\r\n"
    "\n"
    "  # indented comment en_AU fr_FR\n"
    "en_NZ en_NZ:en_GB extra\n"
    "csb_PL csb:pl\n"
    " \ten_AU \t en_AU:en_GB \r\n"
    "en_AU later:entry\n"
    "it_IT it_IT\n"
)


@pytest.mark.parametrize(
    "configured,params,language",
    [
        # localed sets LANGUAGE from its fallback map for a sent LANG without LANGUAGE, replacing the configured one
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_AU"}, "en_AU:en_GB"),
        ({"lang": "en_US.UTF-8"}, {"lang": "en_AU", "lc_time": "C.UTF-8"}, "en_AU:en_GB"),
        # an empty LANGUAGE counts as not set
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_AU", "language": ""}, "en_AU:en_GB"),
        # a requested LANGUAGE is sent with the changed LANG
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_AU", "language": "en_US"}, "en_US"),
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_AU", "language": "fr_FR"}, "fr_FR"),
        # the map is matched exactly, and a line without two fields is ignored
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_AU.UTF-8"}, "en_US"),
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "en_NZ"}, "en_US"),
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "de_DE.UTF-8"}, "en_US"),
        # localed sets the fallback, then drops it as equal to LANG
        ({"lang": "en_US.UTF-8", "language": "en_US"}, {"lang": "it_IT"}, None),
        # an unchanged LANG is not sent, so localed keeps the configured LANGUAGE
        ({"lang": "en_AU", "language": "en_US"}, {"lang": "en_AU", "lc_time": "C.UTF-8"}, "en_US"),
        ({"lang": "en_AU"}, {"lang": "en_AU", "lc_time": "C.UTF-8"}, None),
    ],
)
def test_locale_check_mode_predicts_language_fallback(
    monkeypatch, run_module, keyboard_files, configured, params, language
):
    keyboard_files["language_fallback_map"].write_bytes(LANGUAGE_FALLBACK_MAP.encode())
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value={**LOCALE, "locale": configured}))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": params}, True)
    assert result["changed"] and result["locale"]["locale"]["language"] == language
    mutate.assert_not_called()


# systemd's LONG_LINE_MAX, the length at which read_line() fails
LONG_LINE_MAX = 1024 * 1024


@pytest.mark.parametrize(
    "content,lang,language",
    [
        # strv_split_full() with EXTRACT_UNQUOTE removes quotes and takes the character after a backslash as it is
        (b"\"en AU\" 'en_AU:en_GB'\n", "en AU", "en_AU:en_GB"),
        (b'en_AU "en_AU:"en_GB\n', "en_AU", "en_AU:en_GB"),
        (b"en\\_AU en_AU\\:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"en\\ AU 'it''s'\n", "en AU", "its"),
        (b'en_AU "a \\" b"\n', "en_AU", 'a " b'),
        (b'en_AU ""\n', "en_AU", ""),
        # an unbalanced quote or a trailing backslash ends the lookup without a fallback
        (b'fr_CA "fr_CA:fr_FR\nen_AU en_AU:en_GB\n', "en_AU", None),
        (b"fr_CA 'fr_CA:fr_FR\nen_AU en_AU:en_GB\n", "en_AU", None),
        (b"fr_CA fr_CA:fr_FR\\\nen_AU en_AU:en_GB\n", "en_AU", None),
        (b"fr_CA fr_CA:fr_FR\\ \t\nen_AU en_AU:en_GB\n", "en_AU", None),
        # a comment is skipped before it is split, and an escaped quote is no quote
        (b'# "unbalanced\nfr_CA fr\\" fr_CA:fr_FR\nen_AU en_AU:en_GB\n', "en_AU", "en_AU:en_GB"),
        # a line after the one listing lang is not read
        (b'en_AU en_AU:en_GB\nfr_CA "fr_CA:fr_FR\n', "en_AU", "en_AU:en_GB"),
        # a NUL ends a line as a line break does
        (b"en_AU\0en_AU:en_GB\n", "en_AU", None),
        (b"fr_CA fr_CA:fr_FR\0en_AU en_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"# comment\0en_AU en_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"en_AU en_AU:en_GB\0extra\n", "en_AU", "en_AU:en_GB"),
        # read_line() fails for a line of LONG_LINE_MAX bytes or more, ending the lookup
        (b"#" + b"x" * (LONG_LINE_MAX - 2) + b"\nen_AU en_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"#" + b"x" * (LONG_LINE_MAX - 1) + b"\nen_AU en_AU:en_GB\n", "en_AU", None),
        (b"#" + b"x" * (LONG_LINE_MAX - 1) + b"\ren_AU en_AU:en_GB\n", "en_AU", None),
        (b"#" + b"x" * LONG_LINE_MAX, "en_AU", None),
        # the limit applies to each line, not to a stretch of lines without a line feed
        (b"fr_CA fr_CA:fr_FR\r" * 100000 + b"en_AU en_AU:en_GB\r", "en_AU", "en_AU:en_GB"),
        (b"en_AU en_AU:en_GB\r" + b"fr_CA fr_CA:fr_FR\r" * 100000, "en_AU", "en_AU:en_GB"),
        (b"#" * 65530 + b"\nen_AU en_AU:en_GB", "en_AU", "en_AU:en_GB"),
    ],
)
def test_language_fallback_parses_map_as_systemd(keyboard_files, content, lang, language):
    keyboard_files["language_fallback_map"].write_bytes(content)
    assert systemd_locale.language_fallback(Mock(), lang, 262) == language


@pytest.mark.parametrize(
    "content,lang,language",
    [
        # systemd 239 reads the map with fgets(): a carriage return separates fields, and does not end a line
        (b"en_AU\ren_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"fr_CA fr_CA:fr_FR\ren_AU en_AU:en_GB\n", "en_AU", None),
        (b"en_AU en_AU:en_GB\r\n", "en_AU", "en_AU:en_GB"),
        # a NUL ends the text of the line, not the line
        (b"fr_CA fr_CA:fr_FR\0en_AU en_AU:en_GB\n", "en_AU", None),
        (b"en_AU en_AU:en_GB\0extra\n", "en_AU", "en_AU:en_GB"),
        # a long line is read in pieces of 2047 bytes, each read as a line, and none is too long
        (b"#" + b"x" * 2046 + b"en_AU en_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"#" + b"x" * 2045 + b"en_AU en_AU:en_GB\n", "en_AU", None),
        (b"#" + b"x" * LONG_LINE_MAX + b"\nen_AU en_AU:en_GB\n", "en_AU", "en_AU:en_GB"),
        (b"en_AU en_AU:en_GB", "en_AU", "en_AU:en_GB"),
    ],
)
def test_language_fallback_parses_map_as_systemd_239(keyboard_files, content, lang, language):
    keyboard_files["language_fallback_map"].write_bytes(content)
    assert systemd_locale.language_fallback(Mock(), lang, 239) == language


@pytest.mark.parametrize("kind", ["device", "fifo"])
def test_language_fallback_reads_only_a_regular_file(keyboard_files, kind):
    # reading /dev/zero would never end and opening a FIFO without a writer would block, so neither is read
    if kind == "device":
        keyboard_files["language_fallback_map"].symlink_to("/dev/zero")
    else:
        os.mkfifo(keyboard_files["language_fallback_map"])

    with time_limit():
        assert systemd_locale.language_fallback(Mock(), "en_AU", 262) is None


def test_language_fallback_map_denied_access_fails(monkeypatch, module_factory, invoke, keyboard_files):
    # systemd-localed runs as root and reads a map the module may not, so a denied access is not read as no fallback
    keyboard_files["language_fallback_map"].write_bytes(b"en_AU en_AU:en_GB\n")
    monkeypatch.setattr(systemd_locale, "open_regular", Mock(side_effect=PermissionError(errno.EACCES, "denied")))
    result = invoke(systemd_locale.language_fallback, module_factory(), "en_AU", 262)
    assert result["failed"] and result["msg"].startswith(f"unable to read {keyboard_files['language_fallback_map']}:")


@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_check_mode_with_fifo_language_fallback_map_keeps_language(
    monkeypatch, run_module, keyboard_files, check_mode
):
    os.mkfifo(keyboard_files["language_fallback_map"])
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    configured = {**LOCALE, "locale": {"lang": "en_US.UTF-8", "language": "en_US"}}
    updated = {**LOCALE, "locale": {"lang": "en_AU", "language": "en_US"}}
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(side_effect=[configured, updated]))
    monkeypatch.setattr(systemd_locale, "systemd_call", Mock())

    with time_limit():
        result = run_module(systemd_locale, {"locale": {"lang": "en_AU"}}, check_mode)

    assert result["changed"] and result["locale"]["locale"]["language"] == "en_US"


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "content,lang",
    [
        # systemd-localed writes such a fallback, then fails to read the locale back
        (b"en_AU caf\xe9\n", "en_AU"),
        (b"en_AU \xed\xa0\x80\n", "en_AU"),
        (b"fr_CA fr_CA:fr_FR\nen_AU 'en_AU:\xef\xbf\xbe'\n", "en_AU"),
        (b"en_AU en_AU:\xef\xb7\x90\n", "en_AU"),
    ],
)
def test_locale_fallback_not_valid_utf8_fails_before_any_call(
    monkeypatch, run_module, keyboard_files, content, lang, check_mode
):
    keyboard_files["language_fallback_map"].write_bytes(content)
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    configured = {**LOCALE, "locale": {"lang": "en_US.UTF-8", "language": "en_US"}}
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=configured))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": {"lang": lang, "lc_time": "C.UTF-8"}}, check_mode)
    path = keyboard_files["language_fallback_map"]
    assert result["failed"] and result["msg"] == (
        f"unable to set locale.lang {lang}: {path} lists invalid UTF-8 or a noncharacter, set locale.language"
    )
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "configured,params",
    [
        # a requested LANGUAGE is sent with the changed LANG, so localed does not use the map
        ({"lang": "en_US.UTF-8"}, {"lang": "en_AU", "language": "en_GB"}),
        # an unchanged LANG is not sent
        ({"lang": "en_AU"}, {"lang": "en_AU", "lc_time": "C.UTF-8"}),
        # the fallback of another LANG
        ({"lang": "en_US.UTF-8"}, {"lang": "en_NZ"}),
    ],
)
def test_locale_fallback_not_valid_utf8_for_unsent_lang_is_ignored(
    monkeypatch, run_module, keyboard_files, configured, params
):
    keyboard_files["language_fallback_map"].write_bytes(b"en_AU caf\xe9\n")
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value={**LOCALE, "locale": configured}))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": params})
    assert result["changed"] and not result.get("failed")
    assert mutate.call_args.args[2] == "SetLocale"


def test_locale_check_mode_keeps_language_for_empty_fallback(monkeypatch, run_module, keyboard_files):
    # localed replaces LANGUAGE with the empty fallback, then merges the configured one back in
    keyboard_files["language_fallback_map"].write_bytes(b'en_AU ""\n')
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    configured = {"lang": "en_US.UTF-8", "language": "en_US"}
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value={**LOCALE, "locale": configured}))
    result = run_module(systemd_locale, {"locale": {"lang": "en_AU"}}, True)
    assert result["changed"] and result["locale"]["locale"]["language"] == "en_US"


def test_locale_real_run_returns_language_read_back(monkeypatch, run_module):
    # a real run checks the fallback the map lists but returns the LANGUAGE localed reports
    configured = {**LOCALE, "locale": {"lang": "en_US.UTF-8"}}
    updated = {**LOCALE, "locale": {"lang": "en_AU", "language": "en_GB"}}
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(side_effect=[configured, updated]))
    monkeypatch.setattr(systemd_locale, "language_fallback", Mock(return_value="en_AU:en_GB"))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, {"locale": {"lang": "en_AU"}})
    assert result["changed"] and result["locale"]["locale"]["language"] == "en_GB"
    assert mutate.call_args.args[2:] == ("SetLocale", ["LANG=en_AU"], False)


@pytest.mark.parametrize("directory", [False, True])
def test_locale_check_mode_without_language_fallback_map_keeps_language(
    monkeypatch, run_module, keyboard_files, directory
):
    # localed ignores a map that is missing or that it cannot read, such as a directory
    if directory:
        keyboard_files["language_fallback_map"].mkdir()

    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    configured = {"lang": "en_US.UTF-8", "language": "en_US"}
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value={**LOCALE, "locale": configured}))
    result = run_module(systemd_locale, {"locale": {"lang": "en_AU"}}, True)
    assert result["changed"] and result["locale"]["locale"]["language"] == "en_US"


@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_requires_systemd_239_before_any_write(monkeypatch, run_module, systemd_version, check_mode):
    systemd_version.return_value = 238
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    params = {"locale": {"lc_time": "en_GB.UTF-8"}, "vconsole_keymap": "de"}
    result = run_module(systemd_locale, params, check_mode)
    assert result["failed"] and result["msg"] == "unable to set locale: systemd >= 239 is required, found 238"
    mutate.assert_not_called()


UTF8_RULE = "it must be valid UTF-8 without NUL characters"
NONCHARACTER_RULE = "it must not contain Unicode noncharacters"


@pytest.mark.parametrize(
    "params,option,rule",
    [
        ({"locale": {"lang": "de_DE.UTF-8"}, "x11_layout": "\udc80"}, "x11_layout", UTF8_RULE),
        ({"locale": {"lang": "de_DE.UTF-8"}, "x11_layout": "d\udcc3\udca9"}, "x11_layout", UTF8_RULE),
        ({"locale": {"lang": "de_DE.UTF-8"}, "vconsole_keymap_toggle": "\ud800"}, "vconsole_keymap_toggle", UTF8_RULE),
        ({"locale": {"lang": "de_DE.UTF-8", "lc_time": "\udc80"}}, "locale.lc_time", UTF8_RULE),
        # GLib cuts a D-Bus string at NUL, so de_DE.UTF-8 would be sent and the task would change on every run
        ({"locale": {"lang": "de_DE.UTF-8\x00x"}}, "locale.lang", UTF8_RULE),
        ({"locale": {"lang": "de_DE.UTF-8"}, "vconsole_keymap": "de\x00"}, "vconsole_keymap", UTF8_RULE),
        ({"locale": {"lang": "de_DE.UTF-8"}, "x11_layout": "\x00de"}, "x11_layout", UTF8_RULE),
    ],
)
@pytest.mark.parametrize("dasbus", [False, True])
@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_value_not_valid_utf8_fails_before_any_call(
    monkeypatch, run_module, systemd_version, params, option, rule, dasbus, check_mode
):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", dasbus)
    proxy = Mock(side_effect=AssertionError("must not connect to systemd-localed"))
    monkeypatch.setattr(systemd_locale, "systemd_proxy", proxy)
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    # task-level no_log is what lets such a value past AnsibleModule's invocation logging
    result = run_module(systemd_locale, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"] and result["msg"] == f"invalid {option}: {rule}"
    proxy.assert_not_called()
    systemd_version.assert_not_called()
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "params,option",
    [
        # sd-bus refuses a noncharacter, which for a keyboard value sent after another request leaves that written
        ({"locale": {"lang": "de_DE.UTF-8"}, "x11_options": "grp:\ufffe"}, "x11_options"),
        ({"locale": {"lang": "de_DE.UTF-8"}, "vconsole_keymap": "de\ufdd0"}, "vconsole_keymap"),
        ({"vconsole_keymap": "de", "x11_layout": "de\ufdd0"}, "x11_layout"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_keyboard_noncharacter_after_another_request_fails_before_any_write(
    monkeypatch, run_module, params, option, check_mode
):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, dict(params, _ansible_no_log=True), check_mode)
    assert result["failed"] and result["msg"] == f"invalid {option}: {NONCHARACTER_RULE}"
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "params,method",
    [
        ({"vconsole_keymap": "de\ufdd0"}, "SetVConsoleKeyboard"),
        ({"x11_layout": "de\ufdd0"}, "SetX11Keyboard"),
        # the configured locale matches, so the keyboard request is the first one sent
        ({"locale": {"lang": "en_US.UTF-8"}, "x11_options": "grp:\ufffe"}, "SetX11Keyboard"),
    ],
)
def test_locale_keyboard_noncharacter_in_first_request_is_left_to_systemd(monkeypatch, run_module, params, method):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    calls = []

    def refuse(module, proxy, name, *args):
        calls.append(name)
        module.fail_json(msg=f"unable to call {name}: Bad message")

    monkeypatch.setattr(systemd_locale, "systemd_call", refuse)
    result = run_module(systemd_locale, dict(params, _ansible_no_log=True))
    assert result["failed"] and result["msg"] == f"unable to call {method}: Bad message"
    assert calls == [method]


def test_locale_noncharacter_is_left_to_systemd(monkeypatch, run_module):
    # SetLocale is sent first, and sd-bus refuses the message, so nothing is written
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    calls = []

    def refuse(module, proxy, method, *args):
        calls.append(method)
        module.fail_json(msg=f"unable to call {method}: Bad message")

    monkeypatch.setattr(systemd_locale, "systemd_call", refuse)
    result = run_module(systemd_locale, {"locale": {"lang": "de_DE.UTF-8\ufdd0"}, "x11_layout": "de"})
    assert result["failed"] and result["msg"] == "unable to call SetLocale: Bad message"
    assert calls == ["SetLocale"]


@pytest.mark.parametrize(
    "params,option",
    [
        ({"ntp": False, "timezone": "\udc80"}, "timezone"),
        ({"ntp": False, "time": "2026-07-26 14:30 \ud800"}, "time"),
        ({"ntp": False, "timezone": "UTC\x00x"}, "timezone"),
    ],
)
@pytest.mark.parametrize("dasbus", [False, True])
@pytest.mark.parametrize("check_mode", [False, True])
def test_timedate_value_not_valid_utf8_fails_before_any_call(
    monkeypatch, run_module, params, option, dasbus, check_mode
):
    monkeypatch.setattr(systemd_timedate, "HAS_DASBUS", dasbus)
    proxy = Mock(side_effect=AssertionError("must not connect to systemd-timedated"))
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", proxy)
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, dict(params, _ansible_no_log=True), check_mode)
    rule = UTF8_RULE if option == "timezone" else "it must be valid UTF-8"
    assert result["failed"] and result["msg"] == f"invalid {option}: {rule}"
    proxy.assert_not_called()
    mutate.assert_not_called()


def test_time_with_nul_refused_by_run_command(monkeypatch, run_module):
    # run_command refuses an argument with a NUL before running anything, so nothing is written
    mutate = timedate_module(monkeypatch)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", Mock(return_value="/bin/false"))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    params = {"timezone": "Europe/Berlin", "time": "2026-07-26 14:30\x00", "_ansible_no_log": True}
    result = run_module(systemd_timedate, params)
    # ansible-core 2.11 reports the error itself, later versions a generic message
    assert result["failed"] and result["msg"] in ("Error executing command.", "embedded null byte")
    mutate.assert_not_called()


def test_time_with_escaped_byte_passed_to_systemd_analyze(monkeypatch, tmp_path, run_module):
    # an escaped byte reaches systemd-analyze as that byte, and its refusal comes before any setting is written
    script = tmp_path / "systemd-analyze"
    script.write_text(f"#!/bin/sh\nprintf '%s' \"$3\" > {tmp_path}/argument\necho 'Failed to parse' >&2\nexit 1\n")
    script.chmod(0o755)
    mutate = timedate_module(monkeypatch)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", Mock(return_value=str(script)))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    params = {"timezone": "Europe/Berlin", "time": "14:30 \udcc3", "_ansible_no_log": True}
    result = run_module(systemd_timedate, params)
    assert result["failed"] and result["msg"].endswith("Failed to parse")
    assert (tmp_path / "argument").read_bytes() == b"14:30 \xc3"
    mutate.assert_not_called()


def test_timezone_noncharacter_is_left_to_systemd(monkeypatch, run_module):
    # SetTimezone is sent first, and sd-bus refuses the message, so nothing is written
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value=TIMEDATE))
    calls = []

    def refuse(module, proxy, method, *args):
        calls.append(method)
        module.fail_json(msg=f"unable to call {method}: Bad message")

    monkeypatch.setattr(systemd_timedate, "systemd_call", refuse)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berl\ufdd0", "local_rtc": True})
    assert result["failed"] and result["msg"] == "unable to call SetTimezone: Bad message"
    assert calls == ["SetTimezone"]


def test_time_noncharacter_is_left_to_systemd_analyze(monkeypatch, run_module, analyze):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value=TIMEDATE))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    analyze.return_value = (1, "", 'Failed to parse "2026-07-26 14:30\ufdd0": Invalid argument')
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": "2026-07-26 14:30\ufdd0"})
    assert result["failed"] and result["msg"].startswith("unable to parse the time specification")
    assert analyze.call_args.args[0][-1] == "2026-07-26 14:30\ufdd0"
    mutate.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_proceeds_on_systemd_239(monkeypatch, run_module, systemd_version, check_mode):
    systemd_version.return_value = 239
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    assert run_module(systemd_locale, {"locale": {"lc_time": "en_GB.UTF-8"}}, check_mode)["changed"]
    assert systemd_version.call_count == 1
    if check_mode:
        mutate.assert_not_called()
    else:
        assert mutate.call_args.args[2:] == ("SetLocale", ["LC_TIME=en_GB.UTF-8"], False)


def test_locale_version_checked_only_for_locale_change(monkeypatch, run_module, systemd_version):
    systemd_version.return_value = 238
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    assert run_module(systemd_locale, {"vconsole_keymap": "de"})["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == ["SetVConsoleKeyboard"]


def test_locale_version_not_read_without_change(monkeypatch, run_module, systemd_version):
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    monkeypatch.setattr(systemd_locale, "systemd_call", Mock(side_effect=AssertionError("must not write")))
    params = {"locale": {"lang": "en_US.UTF-8"}, "vconsole_keymap": "us", "x11_layout": "us"}
    assert run_module(systemd_locale, params)["changed"] is False
    systemd_version.assert_not_called()


@pytest.mark.parametrize(
    "params,read",
    [
        # a console change on a host that is not Debian rewrites only /etc/vconsole.conf
        ({"locale": {"lang": "C.UTF-8"}, "vconsole_keymap": "de"}, ["vconsole"]),
        # the first request is refused by systemd-localed before anything is written, so its file is not read
        ({"vconsole_keymap_toggle": "de"}, []),
        # X11 settings that are not converted leave it alone on systemd 252
        ({"vconsole_keymap": "us", "x11_layout": "de"}, []),
    ],
)
def test_locale_reads_only_keyboard_files_rewritten(
    monkeypatch, run_module, keyboard_files, systemd_version, params, read
):
    # an unrelated file that cannot be read, such as a root-only /etc/default/keyboard, must not block the change
    systemd_version.return_value = 252
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    monkeypatch.setattr(systemd_locale, "systemd_call", Mock())
    opened = []
    monkeypatch.setattr(systemd_locale, "read_bytes", lambda module, path: opened.append(path))
    assert run_module(systemd_locale, params)["changed"]
    assert opened == [str(keyboard_files[name]) for name in read]


def test_vconsole_reset_toggle_when_keymap_changes(module_factory):
    current = {**LOCALE, "vconsole_keymap_toggle": "de"}
    module = module_factory({"vconsole_keymap": "us", "vconsole_keymap_toggle": None})
    assert systemd_locale.vconsole_change(module, current) == {"vconsole_keymap": "us", "vconsole_keymap_toggle": ""}


@pytest.mark.parametrize(
    "params,initial_options,converted_options,x11_args",
    [
        # unset X11 values come from the conversion, not from the read before SetVConsoleKeyboard
        (
            {"vconsole_keymap": "de", "x11_options": "grp:alt_shift_toggle"},
            "terminate:ctrl_alt_bksp",
            "terminate:ctrl_alt_bksp",
            ("de", "pc105+inet", "", "grp:alt_shift_toggle", False, False),
        ),
        # a requested X11 value that matched before the conversion is written again
        (
            {"vconsole_keymap": "de", "x11_options": "grp:alt_shift_toggle"},
            "grp:alt_shift_toggle",
            "terminate:ctrl_alt_bksp",
            ("de", "pc105+inet", "", "grp:alt_shift_toggle", False, False),
        ),
        # nothing requested still differs after the conversion
        (
            {"vconsole_keymap": "de", "x11_layout": "de"},
            "terminate:ctrl_alt_bksp",
            "terminate:ctrl_alt_bksp",
            None,
        ),
    ],
)
def test_x11_keyboard_compares_against_converted_settings(
    monkeypatch, run_module, params, initial_options, converted_options, x11_args
):
    initial = {**LOCALE, "x11_model": "pc105+inet", "x11_options": initial_options}
    converted = {**initial, "vconsole_keymap": "de", "x11_layout": "de", "x11_options": converted_options}
    final = {**converted, "x11_options": params.get("x11_options", converted_options)}
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(side_effect=[initial, converted, final]))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    result = run_module(systemd_locale, params)
    assert result["changed"] and result["locale"] == final
    calls = [entry.args[2:] for entry in mutate.call_args_list]
    assert calls[0] == ("SetVConsoleKeyboard", "de", "", True, False)
    assert calls[1:] == ([("SetX11Keyboard", *x11_args)] if x11_args else [])


@pytest.mark.parametrize(
    "current,params,args",
    [
        # a toggle-only change must not convert the unchanged keymap over the configured X11 settings
        ({}, {"vconsole_keymap_toggle": "ru"}, ("us", "ru", False, False)),
        ({}, {"vconsole_keymap": "us", "vconsole_keymap_toggle": "ru"}, ("us", "ru", False, False)),
        ({"vconsole_keymap_toggle": "ru"}, {"vconsole_keymap": "us"}, ("us", "", False, False)),
        ({"vconsole_keymap_toggle": "ru"}, {"vconsole_keymap_toggle": ""}, ("us", "", False, False)),
        # a keymap change is converted into the X11 settings, as localectl set-keymap does
        ({}, {"vconsole_keymap": "de"}, ("de", "", True, False)),
        ({"vconsole_keymap": ""}, {"vconsole_keymap": "us", "vconsole_keymap_toggle": "ru"}, ("us", "ru", True, False)),
    ],
)
@pytest.mark.parametrize("x11", [{}, {"x11_options": "grp:alt_shift_toggle"}])
def test_vconsole_keyboard_converts_only_a_changed_keymap(monkeypatch, run_module, current, params, args, x11):
    initial = {**LOCALE, "x11_layout": "us,ru", "x11_options": "grp:ctrl_shift_toggle", **current}
    status = Mock(return_value=initial)
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", status)
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    assert run_module(systemd_locale, {**params, **x11})["changed"]
    calls = [entry.args[2:] for entry in mutate.call_args_list]
    assert calls[0] == ("SetVConsoleKeyboard", *args)
    # the X11 settings are re-read before SetX11Keyboard only after a conversion
    assert status.call_count == (3 if args[2] and x11 else 2)
    if x11:
        assert calls[1] == ("SetX11Keyboard", "us,ru", "pc105", "", "grp:alt_shift_toggle", False, False)


@pytest.mark.parametrize(
    "params,convert",
    [
        ({"x11_options": "grp:alt_shift_toggle"}, True),
        ({"x11_layout": "de", "x11_options": "grp:alt_shift_toggle"}, True),
        ({"vconsole_keymap": "us", "vconsole_keymap_toggle": "ru", "x11_options": "grp:alt_shift_toggle"}, False),
        ({"vconsole_keymap": "us", "x11_options": "grp:alt_shift_toggle"}, False),
        ({"vconsole_keymap_toggle": "", "x11_options": "grp:alt_shift_toggle"}, False),
    ],
)
def test_x11_keyboard_converts_only_without_console_settings(monkeypatch, run_module, params, convert):
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    assert run_module(systemd_locale, params)["changed"]
    calls = [entry.args[2:] for entry in mutate.call_args_list]
    assert calls[-1][0] == "SetX11Keyboard" and calls[-1][-2:] == (convert, False)


VCONSOLE_UTF8 = b"KEYMAP=us\nFONT=caf\xe9\n"
VCONSOLE_NUL = b"KEYMAP=us\nFONT=ca\x00f\n"
KEYBOARD_UTF8 = b'XKBMODEL="pc105"\nXKBLAYOUT="us"\nBACKSPACE="caf\xe9"\n'


def locale_module(monkeypatch, keyboard_files, systemd_version, file, content, version, debian):
    keyboard_files[file].write_bytes(content)
    systemd_version.return_value = version
    monkeypatch.setattr(systemd_locale, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_locale, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_locale, "locale_status", Mock(return_value=LOCALE))
    monkeypatch.setattr(systemd_locale, "debian_family", Mock(return_value=debian))
    mutate = Mock()
    monkeypatch.setattr(systemd_locale, "systemd_call", mutate)
    return mutate


@pytest.mark.parametrize(
    "file,content,version,debian,params,option,error",
    [
        # SetVConsoleKeyboard rewrites /etc/vconsole.conf
        ("vconsole", VCONSOLE_UTF8, 252, False, {"vconsole_keymap": "de"}, "vconsole_keymap", "not valid UTF-8"),
        ("vconsole", VCONSOLE_NUL, 257, False, {"vconsole_keymap": "de"}, "vconsole_keymap", "NUL byte"),
        ("vconsole", VCONSOLE_UTF8, 257, False, {"vconsole_keymap_toggle": "de"}, "vconsole_keymap_toggle", "UTF-8"),
        # SetX11Keyboard rewrites it to store the converted keymap
        ("vconsole", VCONSOLE_UTF8, 252, False, {"x11_layout": "de"}, "x11_layout", "not valid UTF-8"),
        # and from systemd 253 to copy the X11 settings, also without a conversion
        ("vconsole", VCONSOLE_NUL, 253, False, {"vconsole_keymap": "us", "x11_layout": "de"}, "x11_layout", "NUL"),
        # Debian 12 keeps the X11 settings in /etc/default/keyboard, also for a converted console keymap
        ("keyboard", KEYBOARD_UTF8, 252, True, {"x11_layout": "de"}, "x11_layout", "not valid UTF-8"),
        ("keyboard", KEYBOARD_UTF8, 252, True, {"vconsole_keymap": "de"}, "vconsole_keymap", "not valid UTF-8"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_unloadable_keyboard_file_fails_before_any_write(
    monkeypatch,
    run_module,
    keyboard_files,
    systemd_version,
    file,
    content,
    version,
    debian,
    params,
    option,
    error,
    check_mode,
):
    mutate = locale_module(monkeypatch, keyboard_files, systemd_version, file, content, version, debian)
    result = run_module(systemd_locale, {"locale": {"lang": "C.UTF-8"}, **params}, check_mode)
    assert result["failed"]
    assert result["msg"].startswith(f"unable to set {option}: {keyboard_files[file]} contains ")
    assert error in result["msg"] and result["msg"].endswith("which systemd-localed refuses to rewrite")
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "file,content,version,debian,params,methods",
    [
        # the keyboard request is the first one sent, so systemd-localed refuses it before anything is written
        ("vconsole", VCONSOLE_UTF8, 252, False, {"vconsole_keymap": "de"}, ["SetVConsoleKeyboard"]),
        ("vconsole", VCONSOLE_UTF8, 253, False, {"x11_layout": "de"}, ["SetX11Keyboard"]),
        ("keyboard", KEYBOARD_UTF8, 252, True, {"x11_layout": "de"}, ["SetX11Keyboard"]),
        # the configured locale matches, so nothing is sent before it
        (
            "vconsole",
            VCONSOLE_NUL,
            257,
            False,
            {"locale": {"lang": "en_US.UTF-8"}, "x11_layout": "de"},
            ["SetX11Keyboard"],
        ),
    ],
)
def test_locale_unloadable_keyboard_file_left_to_systemd_for_first_request(
    monkeypatch, run_module, keyboard_files, systemd_version, file, content, version, debian, params, methods
):
    mutate = locale_module(monkeypatch, keyboard_files, systemd_version, file, content, version, debian)
    assert run_module(systemd_locale, params)["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == methods


@pytest.mark.parametrize(
    "file,content,debian,params,option",
    [
        # SetVConsoleKeyboard writes /etc/vconsole.conf, then only logs a refused conversion into the X11 settings
        ("keyboard", KEYBOARD_UTF8, True, {"vconsole_keymap": "de"}, "vconsole_keymap"),
        # SetX11Keyboard writes the X11 settings, then only logs a refused conversion into the console keymap
        ("vconsole", VCONSOLE_UTF8, False, {"x11_layout": "de"}, "x11_layout"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_unloadable_conversion_file_fails_for_first_request(
    monkeypatch, run_module, keyboard_files, systemd_version, file, content, debian, params, option, check_mode
):
    mutate = locale_module(monkeypatch, keyboard_files, systemd_version, file, content, 252, debian)
    result = run_module(systemd_locale, params, check_mode)
    assert result["failed"] and result["msg"].startswith(f"unable to set {option}: {keyboard_files[file]} contains ")
    mutate.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_locale_unloadable_keyboard_file_for_later_keyboard_request(
    monkeypatch, run_module, keyboard_files, systemd_version, check_mode
):
    # SetX11Keyboard follows SetVConsoleKeyboard, so the file it rewrites is checked before either is sent
    mutate = locale_module(monkeypatch, keyboard_files, systemd_version, "keyboard", KEYBOARD_UTF8, 252, True)
    result = run_module(systemd_locale, {"vconsole_keymap_toggle": "de", "x11_layout": "de"}, check_mode)
    assert result["failed"] and result["msg"].startswith(f"unable to set x11_layout: {keyboard_files['keyboard']} ")
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "file,content,version,debian,params,methods",
    [
        # no keyboard change is pending
        ("vconsole", VCONSOLE_UTF8, 257, False, {}, ["SetLocale"]),
        ("vconsole", VCONSOLE_NUL, 257, False, {"vconsole_keymap": "us", "x11_layout": "us"}, ["SetLocale"]),
        # systemd 252 leaves /etc/vconsole.conf alone for X11 settings that are not converted
        (
            "vconsole",
            VCONSOLE_UTF8,
            252,
            False,
            {"vconsole_keymap": "us", "x11_layout": "de"},
            ["SetLocale", "SetX11Keyboard"],
        ),
        # /etc/default/keyboard holds the X11 settings only for Debian's systemd before 253
        ("keyboard", KEYBOARD_UTF8, 252, False, {"x11_layout": "de"}, ["SetLocale", "SetX11Keyboard"]),
        ("keyboard", KEYBOARD_UTF8, 257, True, {"x11_layout": "de"}, ["SetLocale", "SetX11Keyboard"]),
        # a toggle-only change is not converted into the X11 settings
        ("keyboard", KEYBOARD_UTF8, 252, True, {"vconsole_keymap_toggle": "de"}, ["SetLocale", "SetVConsoleKeyboard"]),
    ],
)
def test_locale_unloadable_keyboard_file_without_rewrite(
    monkeypatch, run_module, keyboard_files, systemd_version, file, content, version, debian, params, methods
):
    mutate = locale_module(monkeypatch, keyboard_files, systemd_version, file, content, version, debian)
    assert run_module(systemd_locale, {"locale": {"lang": "C.UTF-8"}, **params})["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == methods


@pytest.mark.parametrize(
    "os_id,like,expected",
    [("debian", "", True), ("ubuntu", "debian", True), ("almalinux", "rhel centos fedora", False)],
)
def test_debian_family_reads_os_release(monkeypatch, os_id, like, expected):
    monkeypatch.setattr(systemd_locale.distro, "id", lambda: os_id)
    monkeypatch.setattr(systemd_locale.distro, "like", lambda: like)
    assert DEBIAN_FAMILY() is expected


@pytest.mark.parametrize("ntp", [False, True])
def test_ntp_change_is_reported_before_time_is_set(monkeypatch, run_module, analyze, ntp):
    calls = Mock()
    calls.systemd_properties.side_effect = [
        {**TIMEDATE, "ntp": not ntp},
        {"ntp": not ntp},
        {"ntp": not ntp},
        {"ntp": ntp},
        {**TIMEDATE, "ntp": ntp},
    ]
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", calls.systemd_properties)
    monkeypatch.setattr(systemd_timedate, "systemd_call", calls.systemd_call)
    monkeypatch.setattr(systemd_timedate, "sleep", calls.sleep)
    params = {"ntp": ntp} if ntp else {"ntp": False, "time": "@1784083200"}
    result = run_module(systemd_timedate, params)
    assert result["changed"] and result["timedate"]["ntp"] is ntp
    names = [entry[0] for entry in calls.mock_calls]
    assert names == [
        "systemd_properties",
        "systemd_call",
        "systemd_properties",
        "sleep",
        "systemd_properties",
        "sleep",
        "systemd_properties",
    ] + (["systemd_call"] if not ntp else []) + ["systemd_properties"]
    if not ntp:
        assert calls.systemd_call.call_args.args[2:] == ("SetTime", 1784083200000000, False, False)


def test_ntp_change_wait_times_out(monkeypatch, run_module, analyze):
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(systemd_timedate, "monotonic", lambda: next(clock))
    monkeypatch.setattr(systemd_timedate, "sleep", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "ntp": True}))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"ntp": False, "time": "@1784083200"})
    assert result["failed"] and "ntp" in result["msg"] and "30 seconds" in result["msg"]
    assert [entry.args[2] for entry in mutate.call_args_list] == ["SetNTP"]


def hostname_module(monkeypatch, tmp_path, current, machine_info=None, etc_hostname=None):
    if machine_info is not None:
        (tmp_path / "machine-info").write_text(machine_info, newline="")

    if etc_hostname is not None:
        (tmp_path / "hostname").write_text(etc_hostname, newline="")

    monkeypatch.setattr(systemd_hostname, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_hostname, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_hostname, "systemd_properties", Mock(return_value=current))
    mutate = Mock()
    monkeypatch.setattr(systemd_hostname, "systemd_call", mutate)
    return mutate


def test_hostname_empty_setting_matches_missing_machine_info(monkeypatch, tmp_path, run_module):
    current = {**HOSTNAME, "chassis": "vm", "icon_name": "computer-vm"}
    mutate = hostname_module(monkeypatch, tmp_path, current)
    params = {"icon_name": "", "deployment": "", "location": "", "pretty_hostname": ""}
    assert run_module(systemd_hostname, params) == {"changed": False, "hostname": current}
    mutate.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_fallback_chassis_is_persisted(monkeypatch, tmp_path, run_module, check_mode):
    current = {**HOSTNAME, "chassis": "vm", "icon_name": "computer-vm"}
    mutate = hostname_module(monkeypatch, tmp_path, current, "PRETTY_HOSTNAME=Old\n")
    result = run_module(systemd_hostname, {"chassis": "vm", "icon_name": "computer-vm"}, check_mode)
    assert result["changed"]
    if check_mode:
        mutate.assert_not_called()
    else:
        assert [entry.args[2:] for entry in mutate.call_args_list] == [
            ("SetChassis", "vm", False),
            ("SetIconName", "computer-vm", False),
        ]


def test_hostname_machine_info_values_are_compared(monkeypatch, tmp_path, run_module):
    machine_info = (
        "# comment\n"
        "CHASSIS=vm\n"
        "DEPLOYMENT=production  \n"
        "ICON_NAME='computer-vm'\n"
        'LOCATION="rack \\"4\\""\n'
        'PRETTY_HOSTNAME="Molecule Test"\n'
    )
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, machine_info)
    params = {
        "chassis": "vm",
        "deployment": "production",
        "icon_name": "computer-vm",
        "location": 'rack "4"',
        "pretty_hostname": "Molecule Test",
    }
    assert not run_module(systemd_hostname, params)["changed"]
    mutate.assert_not_called()


@pytest.mark.parametrize("version,changed", [(252, True), (257, False)])
def test_hostname_machine_info_parsed_as_running_systemd(
    monkeypatch, tmp_path, run_module, systemd_version, version, changed
):
    systemd_version.return_value = version
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, "# note \\\nPRETTY_HOSTNAME=Foo\n")
    assert run_module(systemd_hostname, {"pretty_hostname": "Foo"})["changed"] is changed
    assert bool(mutate.call_count) is changed


@pytest.mark.parametrize(
    "value,version,expected",
    [
        ("web--", 252, "web-"),
        ("web--", 257, "web-"),
        ("web--", 261, "web-"),
        ("web--", 262, "web"),
        ("web.-", 257, "web"),
        ("web-??", 252, "web"),
        ("web-??", 257, "web"),
        ("web-??", 258, "web-??"),
        ("web-$a", 258, "web-a"),
        ("web-$a", 262, "web-$a"),
    ],
)
def test_hostname_cleanup_follows_version(value, version, expected):
    assert systemd_hostname.hostname_cleanup(value, version) == expected


@pytest.mark.parametrize(
    "etc_hostname,value,version,changed",
    [
        ("web--\n", "web", 252, True),
        ("web--\n", "", 252, False),
        ("web--\n", "web", 262, False),
        ("web-??\n", "web", 257, False),
        ("web-??\n", "web-??", 258, False),
    ],
)
def test_hostname_static_hostname_read_as_running_systemd(
    monkeypatch, tmp_path, run_module, systemd_version, etc_hostname, value, version, changed
):
    systemd_version.return_value = version
    status = {**HOSTNAME, "hostname": "web", "static_hostname": "web"}
    mutate = hostname_module(monkeypatch, tmp_path, status, etc_hostname=etc_hostname)
    assert run_module(systemd_hostname, {"static_hostname": value}, True)["changed"] is changed
    mutate.assert_not_called()


# systemd's LONG_LINE_MAX, the length at which read_line() fails
LONG_LINE = 1024 * 1024


@pytest.mark.parametrize(
    "etc_hostname,stored",
    [
        # read_line() fails for a line of LONG_LINE_MAX bytes or more, and systemd-hostnamed then ignores the file
        (b"#" + b"x" * (LONG_LINE - 1) + b"\nweb\n", ""),
        (b"\n" * 3 + b" " * LONG_LINE + b"\rweb\n", ""),
        (b"#" + b"x" * (LONG_LINE - 2) + b"\nweb\n", "web"),
        # a line after the hostname is not read
        (b"web\n" + b"x" * LONG_LINE, "web"),
        # a NUL ends a line as a line break does
        (b"# comment\0web\n", "web"),
    ],
)
def test_hostname_static_hostname_read_line_by_line(monkeypatch, tmp_path, run_module, etc_hostname, stored):
    (tmp_path / "hostname").write_bytes(etc_hostname)
    status = {**HOSTNAME, "hostname": "web", "static_hostname": stored}
    mutate = hostname_module(monkeypatch, tmp_path, status)
    assert run_module(systemd_hostname, {"static_hostname": "web"}, True)["changed"] is (stored != "web")
    assert run_module(systemd_hostname, {"static_hostname": ""}, True)["changed"] is (stored != "")
    mutate.assert_not_called()


@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_hostname_static_hostname_not_a_regular_file_reads_as_unset(monkeypatch, tmp_path, run_module, kind):
    path = tmp_path / "hostname"
    if kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)

    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "hostname": "localhost", "static_hostname": ""})

    with time_limit():
        assert run_module(systemd_hostname, {"static_hostname": ""}, True)["changed"] is False
        assert run_module(systemd_hostname, {"static_hostname": "web"}, True)["changed"] is True

    mutate.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        OSError(errno.ELOOP, "Too many levels of symbolic links"),
        OSError(errno.EIO, "Input/output error"),
        OSError(errno.EISDIR, "Is a directory"),
    ],
)
def test_hostname_static_hostname_unreadable_reads_as_unset(monkeypatch, tmp_path, run_module, error):
    # systemd-hostnamed 246 and later log a file they cannot read and ignore it
    (tmp_path / "hostname").write_text("web\n")
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "hostname": "localhost", "static_hostname": ""})
    monkeypatch.setattr(systemd_hostname, "open_regular", Mock(side_effect=error))
    assert run_module(systemd_hostname, {"static_hostname": ""}, True)["changed"] is False
    assert run_module(systemd_hostname, {"static_hostname": "web"}, True)["changed"] is True
    mutate.assert_not_called()


@pytest.mark.parametrize("error", [PermissionError(errno.EACCES, "denied"), PermissionError(errno.EPERM, "denied")])
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_static_hostname_denied_access_fails(monkeypatch, tmp_path, run_module, error, check_mode):
    # systemd-hostnamed runs as root and reads a file the module may not, so it is not read as unset
    (tmp_path / "hostname").write_text("web\n")
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "hostname": "web", "static_hostname": "web"})
    monkeypatch.setattr(systemd_hostname, "open_regular", Mock(side_effect=error))
    result = run_module(systemd_hostname, {"static_hostname": "web"}, check_mode)
    assert result["failed"] and result["msg"].startswith(f"unable to read {tmp_path / 'hostname'}:")
    mutate.assert_not_called()


def test_hostname_static_hostname_from_device_reads_as_unset(monkeypatch, tmp_path, run_module):
    # /dev/zero is not a regular file, so it is not read; reading it would never end
    (tmp_path / "hostname").symlink_to("/dev/zero")
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "hostname": "localhost", "static_hostname": ""})

    with time_limit():
        assert run_module(systemd_hostname, {"static_hostname": ""}, True)["changed"] is False

    mutate.assert_not_called()


@pytest.mark.parametrize(
    "etc_hostname,stored",
    [
        # systemd 239 keeps '_' and every '-', and ends a line only at a line feed or a NUL
        (b"my_host\n", "my_host"),
        (b"-web-\n", "-web-"),
        (b"web.\n", "web"),
        (b"..web..lab..\n", "web.lab"),
        (b"\rweb\r\n", "web"),
        (b"# comment\rweb\n", ""),
        (b"# comment\0web\n", "web"),
        (b"w\re\rb\n", "web"),
        # it shortens the line to 64 bytes before removing the other characters
        (b"a" * 60 + b"!!!!!bcd\n", "a" * 60),
        (b"\xc3\xa9" * 40 + b"web\n", ""),
    ],
)
def test_hostname_static_hostname_read_as_systemd_239(
    monkeypatch, tmp_path, run_module, systemd_version, etc_hostname, stored
):
    systemd_version.return_value = 239
    (tmp_path / "hostname").write_bytes(etc_hostname)
    status = {**HOSTNAME, "hostname": "web", "static_hostname": stored}
    mutate = hostname_module(monkeypatch, tmp_path, status)
    assert run_module(systemd_hostname, {"static_hostname": "web"}, True)["changed"] is (stored != "web")
    assert run_module(systemd_hostname, {"static_hostname": ""}, True)["changed"] is (stored != "")
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("my_host", "my_host"),
        ("-web-", "-web-"),
        ("web..", "web"),
        (".web", "web"),
        ("web-.lab", "web-.lab"),
        ("a" * 70, "a" * 64),
        ("a" * 63 + "!b", "a" * 63),
    ],
)
def test_hostname_cleanup_239(value, expected):
    assert systemd_hostname.hostname_cleanup(value, 239) == expected


def test_hostname_version_read_only_to_compare(monkeypatch, tmp_path, run_module, systemd_version):
    hostname_module(monkeypatch, tmp_path, HOSTNAME)
    assert run_module(systemd_hostname, {"transient_hostname": "old"})["changed"] is False
    systemd_version.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_empty_chassis_removes_it(monkeypatch, tmp_path, run_module, check_mode):
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "chassis": "vm"}, "CHASSIS=server\n")
    result = run_module(systemd_hostname, {"chassis": ""}, check_mode)
    assert result["changed"]
    if check_mode:
        assert result["hostname"]["chassis"] == ""
        mutate.assert_not_called()
    else:
        assert mutate.call_args.args[2:] == ("SetChassis", "", False)


def test_hostname_empty_chassis_matches_missing_machine_info(monkeypatch, tmp_path, run_module):
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "chassis": "vm"})
    assert run_module(systemd_hostname, {"chassis": ""})["changed"] is False
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "machine_info,pretty_hostname",
    [
        ("PRETTY_HOSTNAME=Taylor's Laptop\n", "Taylor's Laptop"),
        ('PRETTY_HOSTNAME=a"b c"\n', 'a"b c"'),
        ('PRETTY_HOSTNAME="a" "b"\n', "ab"),
        ("PRETTY_HOSTNAME=Laptop\u00a0\n", "Laptop\u00a0"),
        ("PRETTY_HOSTNAME=Taylor\\\n Laptop\n", "Taylor Laptop"),
        ("PRETTY_HOSTNAME=Laptop\r\n", "Laptop"),
    ],
)
def test_hostname_machine_info_parsed_as_systemd(monkeypatch, tmp_path, run_module, machine_info, pretty_hostname):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, machine_info)
    assert not run_module(systemd_hostname, {"pretty_hostname": pretty_hostname})["changed"]
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "params",
    [
        {"chassis": "vm", "deployment": "prod env"},
        {"chassis": "vm", "deployment": "prod/env"},
        {"chassis": "vm", "icon_name": "a/b"},
        {"chassis": "vm", "icon_name": ".."},
        {"chassis": "vm", "icon_name": "back\\slash"},
        {"chassis": "vm", "icon_name": "Taylor's"},
        {"chassis": "vm", "icon_name": 'a"b'},
        {"chassis": "vm", "icon_name": "glob*"},
        {"chassis": "vm", "icon_name": "glob?"},
        {"chassis": "vm", "icon_name": "glob[0]"},
        {"chassis": "vm", "location": "rack\n4"},
        {"chassis": "vm", "pretty_hostname": "bad\tname"},
        {"chassis": "vm", "icon_name": "computer\ufdd0"},
        {"chassis": "vm", "location": "rack\ufffe"},
        {"chassis": "vm", "pretty_hostname": "Laptop\ufdd0"},
        {"chassis": "vm", "pretty_hostname": "Laptop\U0001ffff"},
        # escaped bytes, even ones that form valid UTF-8, cannot be sent by dasbus; no_log lets them reach the module
        {"chassis": "vm", "pretty_hostname": "Caf\udcc3\udca9", "_ansible_no_log": True},
        {"chassis": "vm", "location": "rack\ud800", "_ansible_no_log": True},
        # NUL also needs no_log to reach the module, as syslog refuses it
        {"chassis": "vm", "deployment": "prod\x00", "_ansible_no_log": True},
        {"chassis": "vm", "icon_name": "computer\x00", "_ansible_no_log": True},
        {"chassis": "vm", "location": "rack\x004", "_ansible_no_log": True},
        {"chassis": "vm", "pretty_hostname": "Laptop\x00", "_ansible_no_log": True},
        {"chassis": "vm", "static_hostname": "web\x00", "_ansible_no_log": True},
        {"chassis": "vm", "transient_hostname": "web\x00", "_ansible_no_log": True},
        {"chassis": "vm", "static_hostname": "web\udc80", "_ansible_no_log": True},
        {"chassis": "vm", "transient_hostname": "web-????"},
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_invalid_settings_fail_before_any_write(monkeypatch, tmp_path, run_module, params, check_mode):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    result = run_module(systemd_hostname, params, check_mode)
    option = next(name for name in params if name != "chassis")
    assert result["failed"] and option in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "value,version",
    [
        # systemd before 262 checks only that an icon name is a valid file name, and round-trips these values
        ("back\\slash", 252),
        ("Taylor's", 252),
        ('a"b', 261),
        ("glob*?[0]", 252),
        ("tab\tname", 252),
        ("new\nline", 252),
        ("del\x7f", 252),
        ("x" * 255, 262),
        ("x" * 256, 247),
        ("x" * 4096, 239),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_icon_name_accepted_by_running_systemd(
    monkeypatch, tmp_path, run_module, systemd_version, value, version, check_mode
):
    systemd_version.return_value = version
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    result = run_module(systemd_hostname, {"icon_name": value}, check_mode)
    assert result["changed"] and not result.get("failed")
    if not check_mode:
        assert mutate.call_args.args[2:] == ("SetIconName", value, False)


@pytest.mark.parametrize(
    "value,version",
    [
        ("back\\slash", 262),
        ("glob?", 262),
        ("tab\tname", 262),
        ("x" * 256, 248),
        ("x" * 4097, 247),
        ("a/b", 239),
        ("..", 252),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_icon_name_refused_by_running_systemd_fails_before_any_write(
    monkeypatch, tmp_path, run_module, systemd_version, value, version, check_mode
):
    systemd_version.return_value = version
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    result = run_module(systemd_hostname, {"static_hostname": "new", "icon_name": value}, check_mode)
    assert result["failed"] and result["msg"].startswith(f"invalid icon_name {value!r}:")
    mutate.assert_not_called()


@pytest.mark.parametrize("value", ["a/b", "..", "back\\slash", "x" * 5000])
def test_hostname_icon_name_without_dasbus_is_predicted_unchecked(monkeypatch, tmp_path, run_module, value):
    # without dasbus nothing is known about the stored settings or the order of the requests
    monkeypatch.setattr(systemd_hostname, "HAS_DASBUS", False)
    assert run_module(systemd_hostname, {"icon_name": value}, True) == {"changed": True, "hostname": {}}


@pytest.mark.parametrize(
    "params,method",
    [
        ({"deployment": "prod/env"}, "SetDeployment"),
        ({"icon_name": "a/b"}, "SetIconName"),
        ({"icon_name": "glob?"}, "SetIconName"),
        ({"location": "rack\n4"}, "SetLocation"),
        ({"pretty_hostname": "Laptop\ufdd0", "_ansible_no_log": True}, "SetPrettyHostname"),
        ({"transient_hostname": "-bad"}, "SetHostname"),
        # the stored chassis matches, so the deployment request is the first one sent
        ({"chassis": "server", "deployment": "prod/env"}, "SetDeployment"),
    ],
)
def test_hostname_first_request_is_validated_by_systemd(monkeypatch, tmp_path, run_module, params, method):
    # systemd-hostnamed refuses the first request before anything is written, so the module leaves it the check
    current = {**HOSTNAME, "static_hostname": "", "hostname_source": "transient"}
    hostname_module(monkeypatch, tmp_path, current, "CHASSIS=server\n")
    calls = []

    def refuse(module, proxy, name, *args):
        calls.append(name)
        module.fail_json(msg=f"unable to call {name}: Invalid argument")

    monkeypatch.setattr(systemd_hostname, "systemd_call", refuse)
    result = run_module(systemd_hostname, params)
    assert result["failed"] and result["msg"] == f"unable to call {method}: Invalid argument"
    assert calls == [method]


@pytest.mark.parametrize(
    "machine_info,params",
    [
        # an icon name stored before systemd 262, which refuses it, is not checked when it is not written
        ("ICON_NAME=computer*\n", {"icon_name": "computer*", "chassis": "vm"}),
        ('LOCATION="rack\t4"\n', {"location": "rack\t4", "chassis": "vm"}),
        ("DEPLOYMENT=prod/env\n", {"deployment": "prod/env", "chassis": "vm"}),
    ],
)
def test_hostname_stored_values_are_not_checked(monkeypatch, tmp_path, run_module, machine_info, params):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, machine_info)
    result = run_module(systemd_hostname, params)
    assert result["changed"] and not result.get("failed")
    assert [entry.args[2:] for entry in mutate.call_args_list] == [("SetChassis", "vm", False)]


@pytest.mark.parametrize("value", ["under_score", "-edge-", "a_b.-c"])
def test_hostname_transient_hostname_checked_as_systemd_239(monkeypatch, tmp_path, run_module, systemd_version, value):
    systemd_version.return_value = 239
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "static_hostname": "", "hostname_source": "default"})
    result = run_module(systemd_hostname, {"chassis": "vm", "transient_hostname": value})
    assert result["changed"] and not result.get("failed")
    assert mutate.call_args.args[2:] == ("SetHostname", value, False)


@pytest.mark.parametrize("value", ["under_score", "-edge-", "a..b", "trailing.", "a" * 65])
def test_hostname_transient_hostname_refused_by_systemd_240(monkeypatch, tmp_path, run_module, systemd_version, value):
    systemd_version.return_value = 240
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "static_hostname": "", "hostname_source": "default"})
    result = run_module(systemd_hostname, {"chassis": "vm", "transient_hostname": value})
    assert result["failed"] and result["msg"] == f"invalid transient_hostname {value!r}: it is not a valid hostname"
    mutate.assert_not_called()


@pytest.mark.parametrize("value", ["web-????", "web-$a"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_transient_wildcards_refused(monkeypatch, tmp_path, run_module, value, check_mode):
    # systemd-hostnamed would replace them, so the reported hostname would never match
    mutate = hostname_module(monkeypatch, tmp_path, {**HOSTNAME, "static_hostname": "", "hostname_source": "default"})
    result = run_module(systemd_hostname, {"transient_hostname": value}, check_mode)
    assert result["failed"] and "wildcards" in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize("value", ["-bad", "bad-", "a..b", "trailing.", "under_score", "a" * 65, "web\ufdd0", "web-$a"])
def test_hostname_static_hostname_validated_by_systemd(monkeypatch, tmp_path, run_module, value):
    # SetStaticHostname is sent first, so the value systemd-hostnamed or sd-bus refuses leaves nothing written
    hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    calls = []

    def refuse(module, proxy, method, *args):
        calls.append(method)
        module.fail_json(msg=f"unable to call {method}: Invalid static hostname")

    monkeypatch.setattr(systemd_hostname, "systemd_call", refuse)
    params = {"static_hostname": value, "chassis": "vm", "_ansible_no_log": True}
    result = run_module(systemd_hostname, params)
    assert result["failed"] and result["msg"] == "unable to call SetStaticHostname: Invalid static hostname"
    assert calls == ["SetStaticHostname"]
    assert run_module(systemd_hostname, params, True)["changed"]


@pytest.mark.parametrize("value", ["a" * 64, "web-????", "a--b.example.com", "1", "Server"])
def test_hostname_valid_static_hostname(monkeypatch, tmp_path, run_module, value):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    assert run_module(systemd_hostname, {"static_hostname": value})["changed"]
    assert mutate.call_args.args[2:] == ("SetStaticHostname", value, False)


@pytest.mark.parametrize(
    "reported,etc_hostname,value,changed",
    [
        ("web-3f0a", "web-????\n", "web-????", False),
        ("web-3f0a", "web-3f0a\n", "web-????", True),
        ("web-3f0a", "web-????\n", "web-3f0a", True),
        ("web", "\n# comment\n\n  web \t\r\n", "web", False),
        ("web", "web\nother\n", "other", True),
        ("old", "new", "new", False),
        ("old", "old\n", "new", True),
        ("", None, "", False),
        ("", "# only a comment\n", "", False),
        ("old", "old\n", "", True),
        ("web", "  web.  \n", "web", False),
        ("web-a.example", "-web-a..example-.\n", "web-a.example", False),
        ("webhost", "web_host\n", "webhost", False),
        ("", "-\n", "", False),
        ("", "_\n", "web", True),
        ("web-a1b2", "web-$a\n", "", True),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_static_hostname_compared_with_file(
    monkeypatch, tmp_path, run_module, reported, etc_hostname, value, changed, check_mode
):
    status = {**HOSTNAME, "hostname": reported, "static_hostname": reported}
    mutate = hostname_module(monkeypatch, tmp_path, status, etc_hostname=etc_hostname)
    result = run_module(systemd_hostname, {"static_hostname": value}, check_mode)
    assert result["changed"] is changed
    if changed and not check_mode:
        assert mutate.call_args.args[2:] == ("SetStaticHostname", value, False)
    else:
        mutate.assert_not_called()


def test_hostname_static_hostname_written_first(monkeypatch, tmp_path, run_module):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    params = {"chassis": "vm", "pretty_hostname": "New", "static_hostname": "new"}
    assert run_module(systemd_hostname, params)["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == [
        "SetStaticHostname",
        "SetChassis",
        "SetPrettyHostname",
    ]


@pytest.mark.parametrize(
    "status,etc_hostname,params,methods",
    [
        # SetStaticHostname applies the static hostname, else the default, in place of the transient one
        (HOSTNAME, "old\n", {"static_hostname": "", "transient_hostname": ""}, ["SetStaticHostname"]),
        (
            {**HOSTNAME, "hostname": "dhcp", "hostname_source": "transient", "static_hostname": ""},
            "",
            {"static_hostname": "new", "transient_hostname": ""},
            ["SetStaticHostname"],
        ),
        (
            {**HOSTNAME, "hostname": "dhcp", "hostname_source": "transient", "static_hostname": ""},
            "",
            {"static_hostname": "", "transient_hostname": ""},
            ["SetHostname"],
        ),
        # systemd-hostnamed keeps the hostname source it determined, so it can lag behind /etc/hostname
        (
            {**HOSTNAME, "hostname": "dhcp", "hostname_source": "transient"},
            None,
            {"transient_hostname": ""},
            ["SetHostname"],
        ),
    ],
)
def test_hostname_resets_transient_only_when_static_change_does_not(
    monkeypatch, tmp_path, run_module, status, etc_hostname, params, methods
):
    mutate = hostname_module(monkeypatch, tmp_path, status, etc_hostname=etc_hostname)
    assert run_module(systemd_hostname, params)["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == methods


def test_hostname_check_mode_predicts_static_over_reset_transient(monkeypatch, tmp_path, run_module):
    status = {**HOSTNAME, "hostname": "transient", "hostname_source": "transient", "static_hostname": ""}
    mutate = hostname_module(monkeypatch, tmp_path, status)
    result = run_module(systemd_hostname, {"static_hostname": "new", "transient_hostname": ""}, True)
    assert result["changed"]
    assert result["hostname"]["hostname"] == "new"
    assert result["hostname"]["hostname_source"] == "static"
    mutate.assert_not_called()


def test_time_requires_ntp_disabled_before_any_write(monkeypatch, run_module, analyze):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "ntp": True}))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": "@1"})
    assert result["failed"] and "time" in result["msg"] and "ntp" in result["msg"]
    mutate.assert_not_called()


def test_time_alone_with_ntp_enabled_is_left_to_systemd(monkeypatch, run_module, analyze):
    # SetTime is the first request, so systemd-timedated refuses it before anything is written
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "ntp": True}))
    calls = []

    def refuse(module, proxy, method, *args):
        calls.append(method)
        module.fail_json(msg=f"unable to call {method}: Automatic time synchronization is enabled")

    monkeypatch.setattr(systemd_timedate, "systemd_call", refuse)
    result = run_module(systemd_timedate, {"local_rtc": True, "time": "@1784083200"})
    assert result["failed"] and result["msg"].startswith("unable to call SetTime:")
    assert calls == ["SetTime"]


@pytest.mark.parametrize(
    "current,params,methods",
    [
        # the clock is set before the hardware clock mode, after the time zone, which only systemd-timedated checks
        (TIMEDATE, {"local_rtc": True}, ["SetTime", "SetLocalRTC"]),
        (TIMEDATE, {"timezone": "Europe/Berlin"}, ["SetTimezone", "SetTime"]),
        (TIMEDATE, {"timezone": "Europe/Berlin", "local_rtc": True}, ["SetTimezone", "SetTime", "SetLocalRTC"]),
        # adjusting the system clock from the hardware clock would undo the time set before it
        (
            TIMEDATE,
            {"local_rtc": True, "adjust_system_clock": True},
            ["SetLocalRTC", "SetTime"],
        ),
        (TIMEDATE, {"timezone": "Europe/Berlin", "adjust_system_clock": True}, ["SetTimezone", "SetTime"]),
        # network time synchronization has to be off before the clock is set
        ({**TIMEDATE, "ntp": True}, {"local_rtc": True, "ntp": False}, ["SetLocalRTC", "SetNTP", "SetTime"]),
    ],
)
def test_time_set_before_the_hardware_clock_mode(monkeypatch, run_module, analyze, current, params, methods):
    monkeypatch.setattr(systemd_timedate, "sleep", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    reads = [dict(current), {"ntp": False}, dict(current)]
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(side_effect=reads))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    assert run_module(systemd_timedate, {**params, "time": "@1784083200"})["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == methods


def timedate_module(monkeypatch, current=None, after=None):
    monkeypatch.setattr(systemd_timedate, "HAS_DASBUS", True)
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    reads = [dict(current or TIMEDATE), dict(after or current or TIMEDATE)]
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(side_effect=reads))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    return mutate


@pytest.mark.parametrize(
    "seconds,usec",
    [
        ("@1784083200", 1784083200000000),
        # read as integers, so the microseconds are not rounded through a float
        ("@1784083200.000001", 1784083200000001),
        ("@0.000001", 1),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_time_parsed_by_systemd_analyze(monkeypatch, run_module, analyze, seconds, usec, check_mode):
    mutate = timedate_module(monkeypatch)
    analyze.return_value = (0, analyze_output(seconds), "")
    result = run_module(systemd_timedate, {"time": "2026-07-26 14:30"}, check_mode)
    assert result["changed"]
    assert analyze.call_args.args == (["/usr/bin/systemd-analyze", "timestamp", "--", "2026-07-26 14:30"],)
    assert analyze.call_args.kwargs == {
        "environ_update": {"LC_ALL": "C", "SYSTEMD_COLORS": "0", "TZ": ":UTC"},
        "expand_user_and_vars": False,
    }
    if check_mode:
        assert result["timedate"]["time_usec"] == usec
        mutate.assert_not_called()
        assert analyze.call_count == 1
    else:
        assert [entry.args[2:] for entry in mutate.call_args_list] == [("SetTime", usec, False, False)]
        assert analyze.call_count == 2


@pytest.mark.parametrize(
    "current,params,environ",
    [
        # read in the time zone the host ends up with, as timedatectl does after set-timezone
        (TIMEDATE, {"timezone": "Europe/Berlin"}, {"LC_ALL": "C", "SYSTEMD_COLORS": "0", "TZ": ":Europe/Berlin"}),
        (
            {**TIMEDATE, "timezone": "America/Los_Angeles"},
            {},
            {"LC_ALL": "C", "SYSTEMD_COLORS": "0", "TZ": ":America/Los_Angeles"},
        ),
        ({**TIMEDATE, "timezone": ""}, {}, {"LC_ALL": "C", "SYSTEMD_COLORS": "0"}),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_time_read_in_predicted_timezone(monkeypatch, run_module, analyze, current, params, environ, check_mode):
    timedate_module(monkeypatch, current)
    assert run_module(systemd_timedate, {**params, "time": "14:30"}, check_mode)["changed"]
    for entry in analyze.call_args_list:
        assert entry.kwargs["environ_update"] == environ


FAKE_ANALYZE = """#!/bin/sh
# as systemd 257 prints it, colouring the field names when SYSTEMD_COLORS is set, even on a pipe
if [ "${SYSTEMD_COLORS:-0}" = 0 ]; then on=""; off=""; else on=$(printf '\\033[0;94m'); off=$(printf '\\033[0m'); fi
printf '%s  Original form:%s %s\\n' "$on" "$off" "$3"
printf '%s   UNIX seconds:%s @1784083200\\n' "$on" "$off"
"""


@pytest.mark.parametrize("check_mode", [False, True])
def test_time_parsed_with_systemd_colors_set(monkeypatch, tmp_path, run_module, check_mode):
    # SYSTEMD_COLORS from the task environment must not colour the output systemd-analyze 257 and later print
    script = tmp_path / "systemd-analyze"
    script.write_text(FAKE_ANALYZE)
    script.chmod(0o755)
    monkeypatch.setenv("SYSTEMD_COLORS", "1")
    mutate = timedate_module(monkeypatch)
    monkeypatch.setattr(basic.AnsibleModule, "get_bin_path", Mock(return_value=str(script)))
    monkeypatch.setattr(basic.AnsibleModule, "run_command", RUN_COMMAND)
    result = run_module(systemd_timedate, {"time": "2026-07-26 14:30"}, check_mode)
    assert result["changed"] and not result.get("failed")
    if check_mode:
        assert result["timedate"]["time_usec"] == 1784083200000000
    else:
        assert mutate.call_args.args[2:] == ("SetTime", 1784083200000000, False, False)


def test_time_parsed_again_right_before_it_is_set(monkeypatch, run_module, analyze):
    # now and relative times resolve after the earlier settings and the NTP wait
    monkeypatch.setattr(systemd_timedate, "sleep", Mock())
    mutate = timedate_module(monkeypatch, {**TIMEDATE, "ntp": True})
    monkeypatch.setattr(
        systemd_timedate,
        "systemd_properties",
        Mock(side_effect=[{**TIMEDATE, "ntp": True}, {"ntp": False}, {**TIMEDATE, "ntp": False}]),
    )
    calls = []
    analyze.side_effect = lambda *args, **kwargs: (
        calls.append(mutate.call_count) or (0, analyze_output(f"@{1784083200 + 20 * len(calls)}", "now"), "")
    )
    result = run_module(systemd_timedate, {"ntp": False, "time": "now"})
    assert result["changed"]
    assert calls == [0, 1]
    assert [entry.args[2:] for entry in mutate.call_args_list] == [
        ("SetNTP", False, False),
        ("SetTime", 1784083240000000, False, False),
    ]


@pytest.mark.parametrize("check_mode", [False, True])
def test_time_rejected_by_systemd_analyze_before_any_write(monkeypatch, run_module, analyze, check_mode):
    mutate = timedate_module(monkeypatch)
    error = 'Failed to parse "now UTC": Invalid argument\nHint: this expression is a valid calendar specification.\n'
    analyze.return_value = (1, "", error)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": "now UTC"}, check_mode)
    assert result["failed"]
    assert result["msg"] == f"unable to parse the time specification now UTC: {error.strip()}"
    mutate.assert_not_called()


def test_time_reads_the_last_unix_seconds_field(monkeypatch, run_module, analyze):
    # the original form is echoed first, so a value spanning lines cannot supply the field
    mutate = timedate_module(monkeypatch)
    analyze.return_value = (0, analyze_output("@1784083200", "x\n   UNIX seconds: @5"), "")
    assert run_module(systemd_timedate, {"time": "x"})["changed"]
    assert mutate.call_args.args[2:] == ("SetTime", 1784083200000000, False, False)


@pytest.mark.parametrize("check_mode", [False, True])
def test_time_requires_systemd_analyze_before_any_write(monkeypatch, run_module, check_mode):
    def missing(arg, opt_dirs=None):
        raise ValueError(f"Failed to find required executable {arg}")

    mutate = timedate_module(monkeypatch)
    monkeypatch.setattr(basic, "get_bin_path", missing)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": "now"}, check_mode)
    assert result["failed"] and "systemd-analyze" in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize("seconds", ["@0"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_time_rejects_out_of_range_time_before_any_write(monkeypatch, run_module, analyze, seconds, check_mode):
    mutate = timedate_module(monkeypatch)
    analyze.return_value = (0, analyze_output(seconds, seconds), "")
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": seconds}, check_mode)
    assert result["failed"] and result["msg"] == f"unable to set time: invalid time {seconds}"
    mutate.assert_not_called()


def test_hostname_check_mode_predicts_default_after_clearing_static(monkeypatch, tmp_path, run_module):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    result = run_module(systemd_hostname, {"static_hostname": ""}, True)
    assert result["hostname"]["hostname"] == "localhost"
    assert result["hostname"]["hostname_source"] == "default"
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "machine_info,error",
    [
        # systemd stops reading at the first entry that is not valid UTF-8, keeping the entries before it, but
        # refuses to rewrite the file
        (b"PRETTY_HOSTNAME=Old\nLOCATION=caf\xe9\nCHASSIS=vm\n", "not valid UTF-8"),
        (b"PRETTY_HOSTNAME=Old\nK\xe9Y=1\nCHASSIS=vm\n", "not valid UTF-8"),
        (b"PRETTY_HOSTNAME=Old\nLOCATION='\xed\xa0\x80'\nCHASSIS=vm\n", "not valid UTF-8"),
        (b"PRETTY_HOSTNAME=Old\nLOCATION=\xc0\xaf\nCHASSIS=vm\n", "not valid UTF-8"),
        ("PRETTY_HOSTNAME=Old\nLOCATION=\ufdd0\nCHASSIS=vm\n".encode(), "not valid UTF-8"),
        ("PRETTY_HOSTNAME=Old\nLOCATION=\U0001fffe\nCHASSIS=vm\n".encode(), "not valid UTF-8"),
        (b"PRETTY_HOSTNAME=Old\nLOCATION=\xff", "not valid UTF-8"),
        # systemd refuses to read a file containing a NUL byte
        (b"PRETTY_HOSTNAME=Old\nLOCATION=x\x00\nCHASSIS=vm\n", "NUL byte"),
        (b"PRETTY_HOSTNAME=Old\nCHASSIS=vm\n\x00", "NUL byte"),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_hostname_unloadable_machine_info_fails_before_any_write(
    monkeypatch, tmp_path, run_module, machine_info, error, check_mode
):
    (tmp_path / "machine-info").write_bytes(machine_info)
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    result = run_module(systemd_hostname, {"static_hostname": "new", "chassis": "vm"}, check_mode)
    assert result["failed"] and "chassis" in result["msg"] and "machine-info" in result["msg"]
    assert error in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "machine_info,params",
    [
        # no machine-info setting differs, so the file is not rewritten
        (b"PRETTY_HOSTNAME=Old\nCHASSIS=vm\nLOCATION=\xff", {"chassis": "vm", "pretty_hostname": "Old"}),
        (b"PRETTY_HOSTNAME=Old\nLOCATION=caf\xe9\nCHASSIS=vm\n", {"pretty_hostname": "Old", "chassis": ""}),
        (b"CHASSIS=vm\n\x00", {"chassis": ""}),
    ],
)
def test_hostname_unloadable_machine_info_without_machine_info_change(
    monkeypatch, tmp_path, run_module, machine_info, params
):
    (tmp_path / "machine-info").write_bytes(machine_info)
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    assert run_module(systemd_hostname, {**params, "static_hostname": "new"})["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == ["SetStaticHostname"]


@pytest.mark.parametrize(
    "machine_info",
    [
        # comments and lines without an assignment are not checked
        b"PRETTY_HOSTNAME=Old\n# caf\xe9\nJUNK\xe9\nCHASSIS=vm\n",
        # valid multi-byte values are kept, also when a continuation line splits them
        "PRETTY_HOSTNAME=Old\nLOCATION=caf\u00e9 \U0001f600\nCHASSIS=vm\n".encode(),
        b"PRETTY_HOSTNAME=Old\nLOCATION=\xc3\\\n\xa9\nCHASSIS=vm\n",
        b'PRETTY_HOSTNAME=Old\nLOCATION="\xc3\\\n\xa9"\nCHASSIS=vm\n',
    ],
)
def test_hostname_machine_info_read_as_systemd_bytes(monkeypatch, tmp_path, run_module, machine_info):
    (tmp_path / "machine-info").write_bytes(machine_info)
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    assert run_module(systemd_hostname, {"chassis": "vm", "pretty_hostname": "Old", "location": "x"})["changed"]
    assert [entry.args[2] for entry in mutate.call_args_list] == ["SetLocation"]


@pytest.mark.parametrize(
    "machine_info", [b"LOCATION=\xc3\\\n\xa9\n", b'LOCATION="\xc3\\\n\xa9"\n', b"LOCATION=\xc3\xa9"]
)
def test_hostname_machine_info_joins_bytes_before_decoding(monkeypatch, tmp_path, run_module, machine_info):
    (tmp_path / "machine-info").write_bytes(machine_info)
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    assert run_module(systemd_hostname, {"location": "é"})["changed"] is False
    mutate.assert_not_called()
