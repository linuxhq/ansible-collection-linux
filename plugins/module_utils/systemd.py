# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import re
import stat
import traceback

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.common.text.converters import to_native

DASBUS_IMPORT_ERROR = None

try:
    from dasbus.connection import SystemMessageBus
    from dasbus.error import DBusError
    from gi.repository.GLib import Error as GLibError
except ImportError:
    DASBUS_IMPORT_ERROR = traceback.format_exc()
    HAS_DASBUS = False

    class DBusError(Exception):
        pass

    class GLibError(Exception):
        pass

else:
    HAS_DASBUS = True

INTERFACES = {
    "hostname1": ("org.freedesktop.hostname1", "/org/freedesktop/hostname1"),
    "locale1": ("org.freedesktop.locale1", "/org/freedesktop/locale1"),
    "systemd1": ("org.freedesktop.systemd1", "/org/freedesktop/systemd1"),
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

# systemd's read_line() fails for a line of this many bytes or more
LONG_LINE_MAX = 1024 * 1024

LINE_READ_SIZE = 65536

# the first systemd whose read_line() also ends a line at a carriage return, and reads a pair such as \r\n as one end
READ_LINE_FULL_VERSION = 240

# systemd 240 and later end a line at a line feed, a carriage return or a NUL, taking in at most one of each, with a
# NUL last, so \r\n, \n\r, \r\0 and \n\r\0 each end one line; systemd 239 ends a line at a line feed or a NUL only
LINE_END = re.compile(rb"\0|\n\r?\0?|\r\n?\0?")
LINE_END_239 = re.compile(rb"[\n\0]")

# systemd 239 reads a map line with fgets() into a LINE_MAX buffer, so at most this many bytes at a time
FGETS_SIZE = 2048 - 1

ENV_COMMENTS = "#;"
ENV_NEWLINE = "\n\r"
ENV_SHELL_NEED_ESCAPE = '"\\`$'
ENV_WHITESPACE = " \t\n\r"

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
        module.fail_json(msg=missing_required_lib("dasbus"), exception=DASBUS_IMPORT_ERROR)

    service, path = INTERFACES[interface]

    try:
        bus = SystemMessageBus()
        # get_proxy connects lazily, so connect here to report an unreachable bus
        bus.connection  # noqa: B018
        return bus.get_proxy(service, path)
    except (DBusError, GLibError) as error:
        module.fail_json(msg=f"unable to reach {service} on the system bus: {error}")


def systemd_value(value):
    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255 for item in value)
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
        except (DBusError, GLibError, TimeoutError) as error:
            module.fail_json(msg=f"unable to read the {prop} property: {error}")

        values[name] = systemd_value(value)

    return values


def systemd_version(module):
    """Return the major version of the running systemd, such as 252 for "252.32-1.el9"."""
    proxy = systemd_proxy(module, "systemd1")
    version = systemd_properties(module, proxy, [("version", "Version")])["version"]
    match = re.match(r"\d+", version) if isinstance(version, str) else None

    if not match:
        module.fail_json(msg=f"unable to read the systemd version: unexpected Version property {version!r}")

    return int(match.group())


def systemd_result(module, proxy, method, *args):
    if not hasattr(proxy, method):
        module.fail_json(msg=f"{method} is not supported by this version of systemd")

    try:
        return getattr(proxy, method)(*args)
    except (DBusError, GLibError, TimeoutError) as error:
        module.fail_json(msg=f"unable to call {method}: {error}")


def systemd_call(module, proxy, method, *args):
    systemd_result(module, proxy, method, *args)


def locale_status(module, proxy):
    status = systemd_properties(module, proxy, LOCALE_PROPERTIES)

    variables = dict(entry.split("=", 1) for entry in status["locale"] or [] if "=" in entry)

    status["locale"] = {name: variables.get(name.upper()) for name in LOCALE_VARIABLES}

    return status


def locale_present(variables):
    return {name: value for name, value in variables.items() if value}


def locale_simplify(variables):
    lang = variables.get("lang")

    return {name: value for name, value in variables.items() if value and (name == "lang" or value != lang)}


def locale_setting(variables):
    return [f"{name.upper()}={value}" for name, value in sorted(variables.items())]


def utf8_text(text):
    """Return text decoded with surrogateescape as the UTF-8 systemd's utf8_is_valid() accepts, or None."""
    # bytes split by a continuation line are joined before systemd checks them
    try:
        text = text.encode("utf-8", "surrogateescape").decode("utf-8")
    except UnicodeError:
        return None

    # systemd also refuses noncharacters
    if any(0xFDD0 <= ord(char) <= 0xFDEF or ord(char) & 0xFFFE == 0xFFFE for char in text):
        return None

    return text


def check_utf8(module, settings):
    """Fail naming the first (name, value) setting that cannot be sent to systemd, before any request is made."""
    for name, value in settings:
        # dasbus cannot encode a surrogate, the system bus refuses a string systemd does not accept as UTF-8, such as
        # one with a noncharacter, and a D-Bus string cannot carry NUL, which GLib would cut the value at
        if value and ("\x00" in value or utf8_text(value) != value):
            module.fail_json(
                msg=f"invalid {name}: it must be valid UTF-8 without NUL characters or Unicode noncharacters"
            )


def parse_env_file(text, version):
    """Parse an environment file as systemd's parse_env_file_internal() does, the last assignment winning.

    Return the entries and whether systemd's load_env_file() accepts the file, which it does not when an entry is
    not valid UTF-8.
    """
    entries = {}
    state = "pre_key"
    key = value = ""
    key_space = value_space = None

    def push():
        name = key if key_space is None else key[:key_space]
        entry = value if state != "value" or value_space is None else value[:value_space]

        name = utf8_text(name)
        entry = utf8_text(entry)

        # systemd stops parsing at the first entry that is not valid UTF-8, keeping the entries before it
        if name is None or entry is None:
            return False

        entries[name] = entry
        return True

    for character in text:
        if state == "pre_key":
            if character in ENV_COMMENTS:
                state = "comment"
            elif character not in ENV_WHITESPACE:
                state = "key"
                key = character
                key_space = None

        elif state == "key":
            if character in ENV_NEWLINE:
                state = "pre_key"
            elif character == "=":
                state = "pre_value"
                value = ""
                value_space = None
            else:
                if character not in ENV_WHITESPACE:
                    key_space = None
                elif key_space is None:
                    key_space = len(key)

                key += character

        elif state == "pre_value":
            if character in ENV_NEWLINE:
                if not push():
                    return entries, False

                state = "pre_key"
            elif character == "'":
                state = "single_quote"
            elif character == '"':
                state = "double_quote"
            elif character == "\\":
                state = "value_escape"
            elif character not in ENV_WHITESPACE:
                state = "value"
                value += character

        elif state == "value":
            if character in ENV_NEWLINE:
                if not push():
                    return entries, False

                state = "pre_key"
            elif character == "\\":
                state = "value_escape"
                value_space = None
            else:
                if character not in ENV_WHITESPACE:
                    value_space = None
                elif value_space is None:
                    value_space = len(value)

                value += character

        elif state == "value_escape":
            state = "value"
            if character not in ENV_NEWLINE:
                value += character

        elif state == "single_quote":
            if character == "'":
                state = "pre_value"
            else:
                value += character

        elif state == "double_quote":
            if character == '"':
                state = "pre_value"
            elif character == "\\":
                state = "double_quote_escape"
            else:
                value += character

        elif state == "double_quote_escape":
            state = "double_quote"
            if character in ENV_SHELL_NEED_ESCAPE:
                value += character
            elif character != "\n":
                value += "\\" + character

        elif state == "comment":
            if character == "\\":
                state = "comment_escape"
            elif character in ENV_NEWLINE:
                state = "pre_key"

        elif state == "comment_escape":
            # systemd 253 and earlier continue an escaped comment onto the next line
            state = "pre_key" if character in ENV_NEWLINE and version >= 254 else "comment"

    if state not in ("pre_key", "key", "comment", "comment_escape") and not push():
        return entries, False

    return entries, True


def read_bytes(module, path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None
    except OSError as error:
        module.fail_json(msg=f"unable to read {path}: {to_native(error)}")


def open_regular(path):
    """Open path for reading as bytes, or return None when it is not a regular file, which the module does not read.

    The file is opened without blocking, so a FIFO is detected rather than waited on, and without making a terminal
    the controlling terminal. Raise OSError when it cannot be opened.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC)

    try:
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except OSError:
        os.close(fd)
        raise

    if not regular:
        os.close(fd)
        return None

    return os.fdopen(fd, "rb")


def read_lines(handle, version):
    """Yield the lines of a file as read_line() of the given systemd version reads them, see LINE_END.

    A last line without a line end is yielded once, and a file ending with a line end yields no empty line after it.
    Undecodable bytes are kept as surrogates. Yields None and stops for a line read_line() refuses as too long.
    """
    line_end = LINE_END if version >= READ_LINE_FULL_VERSION else LINE_END_239
    pending = b""

    while True:
        block = handle.read(LINE_READ_SIZE)
        buffer = pending + block
        start = 0

        # each line end found is the first after the line it ends, so the lines between them hold none
        for match in line_end.finditer(buffer):
            line = buffer[start : match.start()]

            if len(line) >= LONG_LINE_MAX:
                yield None
                return

            # a line end at the end of a block can take in more of it from the next block, unless it ends with a NUL
            if block and match.end() == len(buffer) and not match.group().endswith(b"\0"):
                break

            yield line.decode("utf-8", errors="surrogateescape")
            start = match.end()

        pending = buffer[start:]
        line = pending if line_end.search(pending) is None else b""

        if len(line) >= LONG_LINE_MAX:
            yield None
            return

        if not block:
            if line:
                yield line.decode("utf-8", errors="surrogateescape")

            return


def read_map_lines(handle, version):
    """Yield the lines of a map file as systemd-localed's read_next_mapping() of the given version reads them.

    systemd 240 and later read them with read_line(), see read_lines(). systemd 239 reads them with fgets(), so only a
    line feed ends a line, kept at the end of the line, a longer line is read in pieces of FGETS_SIZE bytes, a NUL ends
    the text of a piece, and no line is too long.
    """
    if version >= READ_LINE_FULL_VERSION:
        yield from read_lines(handle, version)
        return

    pending = b""

    while True:
        block = handle.read(LINE_READ_SIZE)
        pending += block

        while pending:
            end = pending.find(b"\n", 0, FGETS_SIZE)

            if end < 0 and len(pending) < FGETS_SIZE and block:
                break

            size = FGETS_SIZE if end < 0 else end + 1
            piece, pending = pending[:size], pending[size:]
            yield piece.split(b"\0", 1)[0].decode("utf-8", errors="surrogateescape")

        if not block:
            return


def load_env_file(content, version):
    """Parse environment file bytes as systemd's load_env_file() does.

    Return the entries and why systemd refuses to load the file, or None when it loads it.
    """
    # systemd refuses to read a file containing a NUL byte, so none of its settings are stored; undecodable bytes
    # are kept as surrogates for the UTF-8 check
    if b"\x00" in content:
        return {}, "contains a NUL byte"

    entries, loadable = parse_env_file(content.decode("utf-8", errors="surrogateescape"), version)

    return entries, None if loadable else "contains a setting that is not valid UTF-8"
