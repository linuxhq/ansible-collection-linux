# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import traceback

from ansible.module_utils.basic import missing_required_lib

DASBUS_IMPORT_ERROR = None

try:
    from dasbus.connection import SystemMessageBus
    from dasbus.error import DBusError
except ImportError:
    DASBUS_IMPORT_ERROR = traceback.format_exc()
    HAS_DASBUS = False

    class DBusError(Exception):
        pass

else:
    HAS_DASBUS = True

INTERFACES = {
    "hostname1": ("org.freedesktop.hostname1", "/org/freedesktop/hostname1"),
    "locale1": ("org.freedesktop.locale1", "/org/freedesktop/locale1"),
    "timedate1": ("org.freedesktop.timedate1", "/org/freedesktop/timedate1"),
}

HOSTNAME_PROPERTIES = [
    ("boot_id", "BootID"),
    ("chassis", "Chassis"),
    ("chassis_asset_tag", "ChassisAssetTag"),
    ("default_hostname", "DefaultHostname"),
    ("deployment", "Deployment"),
    ("firmware_date", "FirmwareDate"),
    ("firmware_vendor", "FirmwareVendor"),
    ("firmware_version", "FirmwareVersion"),
    ("hardware_model", "HardwareModel"),
    ("hardware_sku", "HardwareSKU"),
    ("hardware_vendor", "HardwareVendor"),
    ("hardware_version", "HardwareVersion"),
    ("home_url", "HomeURL"),
    ("hostname", "Hostname"),
    ("hostname_source", "HostnameSource"),
    ("icon_name", "IconName"),
    ("kernel_name", "KernelName"),
    ("kernel_release", "KernelRelease"),
    ("kernel_version", "KernelVersion"),
    ("location", "Location"),
    ("machine_id", "MachineID"),
    ("operating_system_cpe_name", "OperatingSystemCPEName"),
    ("operating_system_fancy_name", "OperatingSystemFancyName"),
    ("operating_system_image_id", "OperatingSystemImageID"),
    ("operating_system_image_version", "OperatingSystemImageVersion"),
    ("operating_system_pretty_name", "OperatingSystemPrettyName"),
    ("operating_system_support_end", "OperatingSystemSupportEnd"),
    ("pretty_hostname", "PrettyHostname"),
    ("static_hostname", "StaticHostname"),
    ("tags", "Tags"),
    ("vsock_cid", "VSockCID"),
]

LOCALE_PROPERTIES = [
    ("locale", "Locale"),
    ("vconsole_keymap", "VConsoleKeymap"),
    ("vconsole_keymap_toggle", "VConsoleKeymapToggle"),
    ("x11_layout", "X11Layout"),
    ("x11_model", "X11Model"),
    ("x11_options", "X11Options"),
    ("x11_variant", "X11Variant"),
]

LOCALE_VARIABLES = [
    "lang",
    "language",
    "lc_address",
    "lc_collate",
    "lc_ctype",
    "lc_identification",
    "lc_measurement",
    "lc_messages",
    "lc_monetary",
    "lc_name",
    "lc_numeric",
    "lc_paper",
    "lc_telephone",
    "lc_time",
]

TIMEDATE_PROPERTIES = [
    ("can_ntp", "CanNTP"),
    ("local_rtc", "LocalRTC"),
    ("ntp", "NTP"),
    ("ntp_synchronized", "NTPSynchronized"),
    ("rtc_time_usec", "RTCTimeUSec"),
    ("time_usec", "TimeUSec"),
    ("timezone", "Timezone"),
]


def systemd_proxy(module, interface):
    if not HAS_DASBUS:
        module.fail_json(
            msg=missing_required_lib("dasbus"), exception=DASBUS_IMPORT_ERROR
        )

    service, path = INTERFACES[interface]

    try:
        return SystemMessageBus().get_proxy(service, path)
    except DBusError as error:
        module.fail_json(msg=f"unable to reach {service} on the system bus: {error}")


def systemd_value(value):
    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    if (
        isinstance(value, list)
        and value
        and all(
            isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255
            for item in value
        )
    ):
        return bytes(value).hex()

    return value


def systemd_properties(module, proxy, properties):
    values = {}

    for name, prop in properties:
        try:
            value = getattr(proxy, prop)
        except AttributeError:
            values[name] = None
            continue
        except DBusError as error:
            module.fail_json(msg=f"unable to read the {prop} property: {error}")

        values[name] = systemd_value(value)

    return values


def systemd_result(module, proxy, method, *args):
    if not hasattr(proxy, method):
        module.fail_json(msg=f"{method} is not supported by this version of systemd")

    try:
        return getattr(proxy, method)(*args)
    except DBusError as error:
        module.fail_json(msg=f"unable to call {method}: {error}")


def systemd_call(module, proxy, method, *args):
    systemd_result(module, proxy, method, *args)


def locale_status(module, proxy):
    status = systemd_properties(module, proxy, LOCALE_PROPERTIES)

    variables = dict(
        entry.split("=", 1) for entry in status["locale"] or [] if "=" in entry
    )

    status["locale"] = {name: variables.get(name.upper()) for name in LOCALE_VARIABLES}

    return status


def locale_present(variables):
    return {name: value for name, value in variables.items() if value}


def locale_simplify(variables):
    lang = variables.get("lang")

    return {
        name: value
        for name, value in variables.items()
        if value and (name == "lang" or value != lang)
    }


def locale_setting(variables):
    return [f"{name.upper()}={value}" for name, value in sorted(variables.items())]
