from copy import deepcopy
from datetime import datetime, timezone
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


def test_clear_static_before_setting_transient(monkeypatch, run_module):
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
        ("now", (0, True)),
        ("1970-01-01 00:00:01 UTC", (1000000, False)),
        ("Thu, 1970-01-01 UTC", (0, False)),
    ],
)
def test_parse_time_specification(module_factory, value, expected):
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
    assert run_module(systemd_locale, {"locale": {"lc_time": "fr_FR.UTF-8"}})["changed"]
    assert mutate.call_args.args[2:] == ("SetLocale", ["LANG=en_US.UTF-8", "LC_TIME=fr_FR.UTF-8"], False)


def test_vconsole_reset_toggle_when_keymap_changes(module_factory):
    current = {**LOCALE, "vconsole_keymap_toggle": "de"}
    module = module_factory({"vconsole_keymap": "us", "vconsole_keymap_toggle": None})
    assert systemd_locale.vconsole_change(module, current) == {"vconsole_keymap": "us", "vconsole_keymap_toggle": ""}


def test_timedate_setter_order_and_arguments(monkeypatch, run_module):
    monkeypatch.setattr(systemd_timedate, "systemd_proxy", Mock())
    monkeypatch.setattr(systemd_timedate, "systemd_properties", Mock(return_value={**TIMEDATE, "ntp": True}))
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


@pytest.mark.parametrize("value", ["@invalid", "+bad", "-bad", "never"])
def test_invalid_time_specification(module_factory, invoke, value):
    result = invoke(systemd_timedate.parse_value, module_factory(), value)
    assert result["failed"] and "unable to parse" in result["msg"]


def hostname_module(monkeypatch, tmp_path, current, machine_info=None):
    path = tmp_path / "machine-info"
    if machine_info is not None:
        path.write_text(machine_info)

    monkeypatch.setattr(systemd_hostname, "MACHINE_INFO", str(path), raising=False)
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
        ("plain", "plain"),
        ("  padded value  ", "padded value"),
        ('"quoted value "', "quoted value "),
        ("'single \\ quoted'", "single \\ quoted"),
        ('"a\\$b\\x"', "a$b\\x"),
        ("escaped\\ space", "escaped space"),
        ("", ""),
    ],
)
def test_machine_info_value(text, expected):
    assert systemd_hostname.machine_info_value(text) == expected


@pytest.mark.parametrize(
    "params",
    [
        {"chassis": "vm", "deployment": "prod env"},
        {"chassis": "vm", "deployment": "prod/env"},
        {"chassis": "vm", "icon_name": "a/b"},
        {"chassis": "vm", "icon_name": ".."},
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
    "current,value,changed",
    [
        ("web-3f0a", "web-????", False),
        ("web-3f0a", "web-???", True),
        ("web-3F0A", "web-????", True),
        ("web-3g0a", "web-????", True),
        ("web-????", "web-????", False),
        ("db-3f0a", "web-????", True),
    ],
)
def test_hostname_wildcard_static_hostname(monkeypatch, tmp_path, run_module, current, value, changed):
    status = {**HOSTNAME, "hostname": current, "static_hostname": current}
    mutate = hostname_module(monkeypatch, tmp_path, status)
    assert run_module(systemd_hostname, {"static_hostname": value})["changed"] is changed
    assert mutate.called is changed


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
    mutate = hostname_module(monkeypatch, tmp_path, HOSTNAME)
    result = run_module(systemd_hostname, {"static_hostname": ""}, True)
    assert result["hostname"]["hostname"] == "localhost"
    assert result["hostname"]["hostname_source"] == "default"
    mutate.assert_not_called()
