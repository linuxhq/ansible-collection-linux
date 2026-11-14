from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from ansible_collections.linuxhq.linux.plugins.modules import (
    systemd_hostname,
    systemd_hostname_info,
    systemd_locale,
    systemd_locale_info,
    systemd_timedate,
    systemd_timedate_info,
)

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
def systemd_version(monkeypatch):
    """Report systemd 262 to the hostname module unless a test sets another version."""
    version = Mock(return_value=262)
    monkeypatch.setattr(systemd_hostname, "systemd_version", version)
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
    result = run_module(systemd_timedate, {"ntp": True})
    assert result["failed"] and "no network time service" in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1h30min", 5400000000),
        ("1.5s", 1500000),
        ("2ms", 2000),
        ("3us", 3),
        ("0", 0),
        ("", None),
        ("1fortnight", None),
        ("bad", None),
    ],
)
def test_parse_duration(value, expected):
    assert systemd_timedate.parse_span(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("@1.5", (1500000, False)),
        ("+2min", (120000000, True)),
        ("-1h", (-3600000000, True)),
        ("now", (1784084400000000, False)),
        ("now UTC", (1784084400000000, False)),
        ("1970-01-01 00:00:01 UTC", (1000000, False)),
        ("Thu, 1970-01-01 UTC", (0, False)),
    ],
)
def test_parse_time_specification(monkeypatch, module_factory, value, expected):
    now = datetime(2026, 7, 15, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(systemd_timedate, "current_time", lambda utc=False: now)
    assert systemd_timedate.parse_value(module_factory(), value) == expected


@pytest.mark.parametrize("origin", [None, "UTC"])
def test_timezone_restored_on_parse_failure(monkeypatch, module_factory, invoke, origin):
    if origin is None:
        monkeypatch.delenv("TZ", raising=False)
    else:
        monkeypatch.setenv("TZ", origin)

    tzset = Mock()
    monkeypatch.setattr(systemd_timedate, "tzset", tzset)
    result = invoke(systemd_timedate.parse_time, module_factory(), "not a timestamp", "Europe/Berlin")
    assert result["failed"]
    assert systemd_timedate.os.environ.get("TZ") == origin
    assert tzset.call_count == 2


def test_relative_day_uses_fixed_clock(monkeypatch, module_factory):
    now = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(systemd_timedate, "current_time", lambda utc=False: now)
    expected = int(datetime(2026, 1, 3, tzinfo=timezone.utc).timestamp() * 1000000)
    assert systemd_timedate.parse_value(module_factory(), "tomorrow UTC") == (expected, False)


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


def test_vconsole_reset_toggle_when_keymap_changes(module_factory):
    current = {**LOCALE, "vconsole_keymap_toggle": "de"}
    module = module_factory({"vconsole_keymap": "us", "vconsole_keymap_toggle": None})
    assert systemd_locale.vconsole_change(module, current) == {"vconsole_keymap": "us", "vconsole_keymap_toggle": ""}


def test_timedate_setter_order_and_arguments(monkeypatch, run_module):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(
        systemd_timedate, "systemd_properties", Mock(side_effect=[{**TIMEDATE, "ntp": True}, {"ntp": False}, TIMEDATE])
    )
    monkeypatch.setattr(systemd_timedate, "parse_time", Mock(return_value=(1500000, True)))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(
        systemd_timedate,
        {"timezone": "Europe/Berlin", "local_rtc": True, "adjust_system_clock": True, "ntp": False, "time": "+1.5s"},
    )
    assert result["changed"]
    assert [entry.args[2:] for entry in mutate.call_args_list] == [
        ("SetTimezone", "Europe/Berlin", False),
        ("SetLocalRTC", True, True, False),
        ("SetNTP", False, False),
        ("SetTime", 1500000, True, False),
    ]
    assert systemd_timedate.parse_time.call_args.args[1:] == ("+1.5s", "Europe/Berlin")


@pytest.mark.parametrize("value", ["@invalid", "+bad", "-bad", "never", "Fri, 1970-01-01 UTC", "Sun 2026-07-27"])
def test_invalid_time_specification(module_factory, invoke, value):
    result = invoke(systemd_timedate.parse_value, module_factory(), value)
    assert result["failed"] and "unable to parse" in result["msg"]


def test_weekday_matches_the_date_in_the_time_zone(module_factory):
    # 08:00 on Sunday in UTC+14 is still Saturday in UTC
    expected = int(datetime(2026, 7, 25, 18, tzinfo=timezone.utc).timestamp() * 1000000)
    result = systemd_timedate.parse_time(module_factory(), "Sun 2026-07-26 08:00", "Pacific/Kiritimati")
    assert result == (expected, False)


@pytest.mark.parametrize("ntp", [False, True])
def test_ntp_change_is_reported_before_time_is_set(monkeypatch, run_module, ntp):
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


def test_time_now_is_taken_after_earlier_changes(monkeypatch, run_module):
    start = datetime(2026, 7, 15, 3, tzinfo=timezone.utc)
    later = start + timedelta(seconds=20)
    clock = Mock(side_effect=[start, start, later, later])
    monkeypatch.setattr(systemd_timedate, "current_time", clock)
    monkeypatch.setattr(systemd_timedate, "sleep", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(
        systemd_timedate,
        "systemd_properties",
        Mock(side_effect=[{**TIMEDATE, "ntp": True}, {"ntp": False}, {**TIMEDATE, "ntp": False}]),
    )
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"ntp": False, "time": "now"})
    assert result["changed"]
    assert [entry.args[2:] for entry in mutate.call_args_list] == [
        ("SetNTP", False, False),
        ("SetTime", int(later.timestamp() * 1000000), False, False),
    ]


def test_ntp_change_wait_times_out(monkeypatch, run_module):
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
    assert systemd_hostname.parse_env_file(text, 262).get("KEY", "") == expected


@pytest.mark.parametrize("version,expected", [(252, ""), (253, ""), (254, "Foo"), (257, "Foo"), (262, "Foo")])
def test_parse_env_file_escaped_comment_follows_version(version, expected):
    text = "# note \\\nPRETTY_HOSTNAME=Foo\n"
    assert systemd_hostname.parse_env_file(text, version).get("PRETTY_HOSTNAME", "") == expected


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
        {"chassis": "vm", "static_hostname": "-bad"},
        {"chassis": "vm", "static_hostname": "bad-"},
        {"chassis": "vm", "static_hostname": "a..b"},
        {"chassis": "vm", "static_hostname": "a.-b"},
        {"chassis": "vm", "static_hostname": "trailing."},
        {"chassis": "vm", "static_hostname": "under_score"},
        {"chassis": "vm", "static_hostname": "a" * 65},
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


def test_hostname_check_mode_predicts_static_over_reset_transient(monkeypatch, tmp_path, run_module):
    status = {**HOSTNAME, "hostname": "transient", "hostname_source": "transient", "static_hostname": ""}
    mutate = hostname_module(monkeypatch, tmp_path, status)
    result = run_module(systemd_hostname, {"static_hostname": "new", "transient_hostname": ""}, True)
    assert result["changed"]
    assert result["hostname"]["hostname"] == "new"
    assert result["hostname"]["hostname_source"] == "static"
    mutate.assert_not_called()


def test_time_requires_ntp_disabled_before_any_write(monkeypatch, run_module):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "ntp": True}))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": "@1"})
    assert result["failed"] and "time" in result["msg"] and "ntp" in result["msg"]
    mutate.assert_not_called()


@pytest.mark.parametrize("value", ["@0", "@-5", "1970-01-01 00:00:00 UTC"])
def test_time_rejects_absolute_epoch_before_any_write(monkeypatch, run_module, value):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value=TIMEDATE))
    mutate = Mock()
    monkeypatch.setattr(systemd_timedate, "systemd_call", mutate)
    result = run_module(systemd_timedate, {"timezone": "Europe/Berlin", "time": value})
    assert result["failed"] and "invalid absolute time" in result["msg"]
    mutate.assert_not_called()


def test_hostname_check_mode_predicts_default_after_clearing_static(monkeypatch, tmp_path, run_module):
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME, etc_hostname="old\n")
    result = run_module(systemd_hostname, {"static_hostname": ""}, True)
    assert result["hostname"]["hostname"] == "localhost"
    assert result["hostname"]["hostname_source"] == "default"
    mutate.assert_not_called()
