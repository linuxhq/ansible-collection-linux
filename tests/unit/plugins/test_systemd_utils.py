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
