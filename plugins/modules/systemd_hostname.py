#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_hostname
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.4.0"
short_description: Manage the systemd hostname
description:
  - Manage the hostname settings owned by C(systemd-hostnamed), the same ones
    C(hostnamectl set-*) writes, by calling the C(org.freedesktop.hostname1)
    interface on the system bus directly.
  - Settings are compared against their stored values and only the ones that
    differ are written, options left unset are not touched.
  - O(chassis), O(deployment), O(icon_name), O(location) and O(pretty_hostname)
    are compared against C(/etc/machine-info), the file C(systemd-hostnamed)
    stores them in, rather than the properties it reports, because it reports a
    computed fallback for a setting that is not stored, such as a chassis
    detected from the firmware or an icon name derived from the chassis. A
    missing file means no setting is stored. The file is
    parsed as the running systemd version parses it, which ignores everything
    from the first setting that is not valid UTF-8, and a whole file
    containing a NUL byte, except systemd 239, which parses the file up to the
    NUL byte.
  - C(systemd-hostnamed) refuses to rewrite C(/etc/machine-info) when it
    contains a setting that is not valid UTF-8, or on systemd 240 and later a
    NUL byte, so changing O(chassis), O(deployment), O(icon_name),
    O(location) or O(pretty_hostname) then fails before any setting is
    written, also in check mode. systemd 239 to 245 also fail to start
    C(systemd-hostnamed) with such a file.
  - O(static_hostname) is compared against C(/etc/hostname), the file
    C(systemd-hostnamed) stores it in, read as systemd reads it, from the first
    line that is neither empty nor a comment, with surrounding whitespace and
    invalid characters removed as the running systemd version removes them,
    so systemd 239, which ends a line only at a line feed or a NUL, also
    keeps V(_) and every V(-). A missing file, or one without a valid
    hostname, means no static hostname is stored. So does a file the module
    cannot read for a reason other than a denied access, such as one with a
    line of 1 MiB or more before the hostname, or an I/O error. A file the
    module may not read fails the task, as C(systemd-hostnamed) runs as root
    and reads it.
  - C(systemd-hostnamed) 246 and later ignore a C(/etc/hostname) they cannot
    read or whose first hostname line is not a valid hostname. systemd 239
    to 245 instead fail to start C(systemd-hostnamed) on any such error other
    than a missing file, including a first hostname line that is left empty
    once invalid characters are removed. They also read C(/etc/hostname)
    and C(/etc/machine-info) only when C(systemd-hostnamed) starts, so a
    change made outside it is not reported until it restarts, as it does
    after exiting when idle, while the module reads the files on every run.
    When either file is edited outside C(systemd-hostnamed) while it runs,
    it drops a request for the value it still holds, leaving the edit in
    place, so the module reports a change on every run until
    C(systemd-hostnamed) exits, about 30 seconds after its last request.
    systemd 246 and later check the files before each request and read
    them again when their size, modification time or inode has changed.
    systemd 246 compares the modification time in whole seconds, so it
    misses an edit that keeps the size within the same second.
  - Only the settings that differ from their stored values are written, in
    the order O(static_hostname), O(chassis), O(deployment), O(icon_name),
    O(location), O(pretty_hostname) and O(transient_hostname). The first of
    them is validated by C(systemd-hostnamed), so a value the running systemd
    refuses fails before anything is changed, and in check mode is reported
    as a change. The module checks each later one before any setting is
    written, so an invalid value fails without leaving earlier settings
    applied. A stored value the running systemd would now refuse, such as an
    icon name stored before an upgrade, is neither written nor checked.
  - With no options set the module reads the current settings and reports no
    change.
notes:
  - Requires a running C(systemd-hostnamed) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
  - Reads the running systemd version from the C(Version) property of
    C(org.freedesktop.systemd1), the service manager, when it compares a
    setting. After systemd is upgraded without a reboot or
    C(systemctl daemon-reexec), the service manager still reports the earlier
    version while a restarted C(systemd-hostnamed) runs the new one, so the
    files are then read as the earlier version reads them.
options:
  chassis:
    description:
      - Chassis type of the machine.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
    choices:
      - ""
      - container
      - convertible
      - desktop
      - embedded
      - handset
      - laptop
      - server
      - tablet
      - vm
      - watch
  deployment:
    description:
      - Deployment environment of the machine, such as V(development) or
        V(production).
      - Only letters, digits, V(-), V(.) and V(:) are allowed.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  icon_name:
    description:
      - Icon name of the machine, following the XDG icon naming specification.
      - Must be a valid file name, so it cannot contain V(/) and cannot be
        V(.) or V(..). systemd 248 and later allow at most 255 bytes, and
        earlier versions at most 4096.
      - Unicode noncharacters, such as U+FDD0 or U+FFFE, are not allowed.
      - systemd 262 and later also refuse control characters, V(\\), V('),
        V("), V(*), V(?) and V([), which earlier versions accept.
      - systemd 241 to 246 read V($), V(`) and V(\\) back from
        C(/etc/machine-info) with an added backslash, so the module refuses
        them there before any setting is written, also in check mode.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  location:
    description:
      - Physical location of the machine, such as a rack or room name.
      - Control characters and Unicode noncharacters, such as U+FDD0 or
        U+FFFE, are not allowed.
      - systemd 241 to 246 read V($), V(`) and V(\\) back from
        C(/etc/machine-info) with an added backslash, so the module refuses
        them there before any setting is written, also in check mode.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  pretty_hostname:
    description:
      - Free-form UTF-8 hostname for presentation, such as V(Taylor's Laptop), as
        C(hostnamectl hostname --pretty) sets.
      - Control characters and Unicode noncharacters, such as U+FDD0 or
        U+FFFE, are not allowed.
      - systemd 241 to 246 read V($), V(`) and V(\\) back from
        C(/etc/machine-info) with an added backslash, so the module refuses
        them there before any setting is written, also in check mode.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  static_hostname:
    description:
      - Static hostname written to C(/etc/hostname), as
        C(hostnamectl hostname --static) sets.
      - C(systemd-hostnamed) applies it as the transient hostname as well, so
        RV(hostname) follows it.
      - C(systemd-hostnamed) validates it. systemd 240 and later accept a
        hostname of at most 64 characters, made of labels of letters, digits
        and V(-) separated by V(.), where no label is empty or starts or ends
        with V(-). systemd 239 also accepts V(_) and a label starting or
        ending with V(-).
      - It must not contain a NUL character. A Unicode noncharacter is
        refused by systemd's D-Bus library.
      - Each V(?) is a wildcard that C(systemd-hostnamed) replaces with a
        hexadecimal character derived from the machine ID. It requires systemd
        258 or later, and older versions refuse it. systemd 262 and later
        also accept labels starting with V($) as tokens they replace.
        C(/etc/hostname) keeps the V(?) and V($) characters, so the option is
        compared as written. In check mode the predicted RV(hostname) keeps
        them.
      - An empty string removes C(/etc/hostname).
    type: str
  transient_hostname:
    description:
      - Transient hostname, as C(hostnamectl hostname --transient) sets.
      - Must be a valid hostname of at most 64 characters, made of labels of
        letters, digits and V(-) separated by V(.), where no label is empty or
        starts or ends with V(-). systemd 239 also accepts V(_) and a label
        starting or ending with V(-).
      - The V(?) wildcard and V($) tokens, which systemd 258 and later accept
        in some hostnames, are not accepted by this module, as
        C(systemd-hostnamed) would replace them, so the hostname it reports
        would never match.
      - C(/etc/hostname) takes the highest preference in C(systemd-hostnamed), so
        a transient hostname cannot take effect while a static one is configured.
        systemd 247 and earlier instead prefer the transient hostname to a
        static hostname naming the local host, ignoring case, such as
        V(localhost), V(localhost.localdomain) or a name ending in
        V(.localhost), each with or without a trailing V(.).
      - Nothing is done when RV(hostname) already matches, whatever the source.
        When it differs and a static hostname that takes precedence is
        configured, this fails rather than reporting a change it cannot make, so
        set O(static_hostname) to the same value instead, either on its own or
        alongside.
      - It cannot be combined with changing O(static_hostname) to a value
        containing a V(?) wildcard or a V($) token, as the module cannot
        predict the hostname
        C(systemd-hostnamed) expands it to, so that fails even when the
        expanded hostname would match. Once the static hostname is configured,
        a matching RV(hostname) is reported as no change.
      - An empty string resets it to the default hostname. While a static
        hostname is in effect there is nothing observable to reset, so it is
        reported as no change.
      - An empty string requires the C(HostnameSource) property of
        C(systemd-hostnamed), added in systemd 248. On older systemd it
        always fails before any setting is written, also in check mode.
    type: str
requirements:
  - dasbus
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: When dasbus is unavailable, predicts changes from the supplied options without querying current state.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure the hostname is managed
  linuxhq.linux.systemd_hostname:
    static_hostname: server.example.com

- name: Ensure the machine information is managed
  linuxhq.linux.systemd_hostname:
    chassis: server
    deployment: production
    icon_name: computer-server
    location: rack 4
    pretty_hostname: Example Server
    static_hostname: server.example.com
"""

RETURN = r"""
hostname:
  description:
    - Hostname settings reported by C(systemd-hostnamed).
    - Properties the running systemd does not implement are returned as V(none).
    - In check mode, the settings that would change are predicted from the
      options, so a setting being removed is predicted as an empty string
      even when C(systemd-hostnamed) then reports a computed fallback.
    - Empty when dasbus is unavailable in check mode.
    - Empty when the module fails after it has changed a setting. Not returned
      when it fails before changing one.
  returned: unless the module fails before changing a setting
  type: dict
  contains:
    boot_id:
      description:
        - Boot ID, as C(BootID) reports it.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    chassis:
      description:
        - Chassis type, such as C(server) or C(vm).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    chassis_asset_tag:
      description:
        - Asset tag of the chassis.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    default_hostname:
      description:
        - Hostname used when no static or transient hostname is set.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    deployment:
      description:
        - Deployment environment, such as C(production).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    firmware_date:
      description:
        - Firmware release date in microseconds since the epoch.
        - V(18446744073709551615), the largest unsigned 64-bit value, when the
          firmware date is unknown.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: int
    firmware_vendor:
      description:
        - Firmware vendor.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    firmware_version:
      description:
        - Firmware version.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hardware_model:
      description:
        - Hardware model.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hardware_sku:
      description:
        - Hardware SKU.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hardware_vendor:
      description:
        - Hardware vendor.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hardware_version:
      description:
        - Hardware version.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    home_url:
      description:
        - Home page of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hostname:
      description:
        - Hostname in effect, the kernel hostname.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    hostname_source:
      description:
        - Source of the hostname in effect, C(static), C(transient) or
          C(default).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    icon_name:
      description:
        - Icon name of the host.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    kernel_name:
      description:
        - Kernel name, such as C(Linux).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    kernel_release:
      description:
        - Kernel release.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    kernel_version:
      description:
        - Kernel version.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    location:
      description:
        - Location of the host.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    machine_id:
      description:
        - Machine ID, as C(MachineID) reports it.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_cpe_name:
      description:
        - CPE name of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_fancy_name:
      description:
        - Fancy name of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_image_id:
      description:
        - Image ID of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_image_version:
      description:
        - Image version of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_pretty_name:
      description:
        - Pretty name of the operating system.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    operating_system_support_end:
      description:
        - End of support of the operating system in microseconds since the
          epoch.
        - V(18446744073709551615), the largest unsigned 64-bit value, when it
          is unknown, such as when C(os-release) sets no C(SUPPORT_END).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: int
    pretty_hostname:
      description:
        - Pretty hostname.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    static_hostname:
      description:
        - Static hostname from C(/etc/hostname).
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: str
    tags:
      description:
        - Tags of the host.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: list
      elements: str
    vsock_cid:
      description:
        - VSOCK context ID of the host.
        - V(4294967295), C(VMADDR_CID_ANY), when the host has no VSOCK context
          ID, such as when it has no VSOCK device.
      returned: >-
        always, as V(none) when the running systemd does not implement it
      type: int
  sample:
    boot_id: 8d1e0f2a4b6c4d0e9f2a3b4c5d6e7f80
    chassis: vm
    chassis_asset_tag: null
    default_hostname: localhost
    deployment: production
    firmware_date: 18446744073709551615
    firmware_vendor: ''
    firmware_version: ''
    hardware_model: ''
    hardware_sku: null
    hardware_vendor: ''
    hardware_version: null
    home_url: https://almalinux.org/
    hostname: server.example.com
    hostname_source: static
    icon_name: computer-vm
    kernel_name: Linux
    kernel_release: 6.12.0-55.40.1.el10_0.aarch64
    kernel_version: '#1 SMP PREEMPT_DYNAMIC Tue Oct 21 04:45:09 CDT 2025'
    location: rack 4
    machine_id: 3f0a1b2c3d4e4f60918293a4b5c6d7e8
    operating_system_cpe_name: cpe:/o:almalinux:almalinux:10::baseos
    operating_system_fancy_name: null
    operating_system_image_id: null
    operating_system_image_version: null
    operating_system_pretty_name: AlmaLinux 10.0 (Purple Lion)
    operating_system_support_end: 2064268800000000
    pretty_hostname: Example Server
    static_hostname: server.example.com
    tags: null
    vsock_cid: 4294967295
"""

import re
import string

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    ENV_QUOTE_ESCAPE_VERSION,
    ENV_SHELL_ESCAPE_VERSION,
    ENV_SHELL_NEED_ESCAPE,
    ENV_WHITESPACE,
    HAS_DASBUS,
    HOSTNAME_PROPERTIES,
    check_utf8,
    load_env_file,
    read_bytes,
    read_lines,
    systemd_call,
    systemd_properties,
    systemd_proxy,
    systemd_version,
)

HOSTNAME_FILE = "/etc/hostname"
MACHINE_INFO = "/etc/machine-info"

MACHINE_INFO_KEYS = {
    "CHASSIS": "chassis",
    "DEPLOYMENT": "deployment",
    "ICON_NAME": "icon_name",
    "LOCATION": "location",
    "PRETTY_HOSTNAME": "pretty_hostname",
}

SETTINGS = [
    ("static_hostname", "SetStaticHostname"),
    ("chassis", "SetChassis"),
    ("deployment", "SetDeployment"),
    ("icon_name", "SetIconName"),
    ("location", "SetLocation"),
    ("pretty_hostname", "SetPrettyHostname"),
]

# systemd-hostnamed writes these quoted in /etc/machine-info, where systemd 241 to 246 read '$', '`' and '\\' back with
# the backslash that escapes them
QUOTED_SETTINGS = ["icon_name", "location", "pretty_hostname"]
SHELL_ESCAPED = frozenset(ENV_SHELL_NEED_ESCAPE) - {'"'}

STRING_SETTINGS = ["deployment", "icon_name", "location", "pretty_hostname", "static_hostname", "transient_hostname"]

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
DEPLOYMENT = re.compile(r"[A-Za-z0-9.:-]+\Z")
HOSTNAME_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
HOSTNAME = re.compile(rf"{HOSTNAME_LABEL}(?:\.{HOSTNAME_LABEL})*\Z")
# systemd 239 also accepts '_' and a label starting or ending with '-'
HOSTNAME_239 = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\Z")
HOSTNAME_CHARACTERS = frozenset(string.ascii_letters + string.digits)
HOSTNAME_CHARACTERS_239 = HOSTNAME_CHARACTERS | frozenset("-_")
# the first systemd that keeps only letters, digits and hyphens between dots in a hostname it reads
HOSTNAME_LDH_VERSION = 240
HOSTNAME_MAX = 64
# systemd 247 and earlier accept an icon name of up to FILENAME_MAX bytes, later ones up to NAME_MAX bytes
FILENAME_MAX = 4096
ICON_NAME_MAX_VERSION = 248
NAME_MAX = 255
# the first systemd that also refuses control characters, backslashes, quotes and glob characters in an icon name
ICON_NAME_SAFE_VERSION = 262
ICON_NAME_UNSAFE = re.compile(r"[\x00-\x1f\x7f\\'\"*?\[]")
# systemd 247 and earlier prefer a transient hostname to a static one that is_localhost() matches, ignoring ASCII case,
# as one of these names or as a name ending in "." and one of them; later ones always apply a static hostname
LOCALHOST_NAMES = (b"localhost", b"localhost.", b"localhost.localdomain", b"localhost.localdomain.")
STATIC_PRECEDENCE_VERSION = 248


def hostname_valid(value, version):
    """Return whether systemd-hostnamed of the given version accepts value as a hostname, without wildcards."""
    pattern = HOSTNAME if version >= HOSTNAME_LDH_VERSION else HOSTNAME_239
    return len(value) <= HOSTNAME_MAX and pattern.match(value) is not None


def static_takes_precedence(static_hostname, version):
    """Return whether systemd-hostnamed of the given version applies static_hostname in place of a transient one."""
    if not static_hostname:
        return False

    if version >= STATIC_PRECEDENCE_VERSION:
        return True

    # bytes.lower() folds only ASCII letters, as strcasecmp() does
    name = static_hostname.encode("utf-8").lower()
    return not (name in LOCALHOST_NAMES or name.endswith(tuple(b"." + local for local in LOCALHOST_NAMES)))


def check_icon_name(module, value, version):
    """Fail when systemd-hostnamed of the given version refuses value as icon_name."""
    if value in (".", "..") or "/" in value:
        module.fail_json(msg=f"invalid icon_name {value!r}: it must be a valid file name")

    if len(value.encode("utf-8")) > (NAME_MAX if version >= ICON_NAME_MAX_VERSION else FILENAME_MAX):
        module.fail_json(msg=f"invalid icon_name {value!r}: it is longer than systemd {version} allows for a file name")

    if version >= ICON_NAME_SAFE_VERSION and ICON_NAME_UNSAFE.search(value):
        module.fail_json(
            msg=f"invalid icon_name {value!r}: systemd {version} refuses control characters, backslashes, quotes and glob characters in it"
        )


def check_setting(module, param, value, version):
    """Fail when systemd-hostnamed of the given version or sd-bus refuses value for param.

    Such a refusal leaves nothing written when its request is the first one sent, so this is checked only for a
    request sent after another, whose refusal would otherwise leave the earlier settings written.
    """
    if not value:
        return

    if param in ("location", "pretty_hostname") and CONTROL_CHARACTERS.search(value):
        module.fail_json(msg=f"invalid {param}: control characters are not allowed")

    if param == "deployment" and not DEPLOYMENT.match(value):
        module.fail_json(msg=f"invalid deployment {value!r}: only letters, digits, '-', '.' and ':' are allowed")

    if param == "icon_name":
        check_icon_name(module, value, version)

    if param in ("icon_name", "location", "pretty_hostname"):
        check_utf8(module, [(param, value)])

    if param == "transient_hostname" and not hostname_valid(value, version):
        module.fail_json(msg=f"invalid transient_hostname {value!r}: it is not a valid hostname")


def read_machine_info(module, version):
    """Return the stored settings and why systemd-hostnamed refuses to rewrite the file, or None."""
    entries, error = load_env_file(read_bytes(module, MACHINE_INFO) or b"", version)

    return {param: entries.get(key, "") for key, param in MACHINE_INFO_KEYS.items()}, error


def hostname_cleanup_239(value):
    """Normalize a hostname as hostname_cleanup() of systemd 239 does."""
    # systemd 239 first shortens the line to 64 bytes, then keeps '_' and every '-', and drops one trailing '.'
    value = value.encode("utf-8", "surrogateescape")[:HOSTNAME_MAX].decode("utf-8", "surrogateescape")
    result = []
    dot = True

    for character in value:
        if character == ".":
            if dot:
                continue

            result.append(character)
            dot = True
        elif character in HOSTNAME_CHARACTERS_239:
            result.append(character)
            dot = False

    if dot and result:
        result.pop()

    return "".join(result)


def hostname_cleanup(value, version):
    """Normalize a hostname as hostname_cleanup() of the given systemd version does."""
    if version < HOSTNAME_LDH_VERSION:
        return hostname_cleanup_239(value)

    # systemd 258 and later keep '?' wildcards, and 262 and later '$' tokens too
    allowed = HOSTNAME_CHARACTERS | frozenset("?$" if version >= 262 else "?" if version >= 258 else "")
    result = []
    dot = hyphen = True

    for character in value:
        if len(result) >= HOSTNAME_MAX:
            break

        if character == ".":
            if dot or hyphen:
                continue

            result.append(character)
            dot, hyphen = True, False
        elif character == "-":
            if dot:
                continue

            result.append(character)
            dot, hyphen = False, True
        elif character in allowed:
            result.append(character)
            dot = hyphen = False

    # systemd 261 and earlier drop only one trailing '-' or '.'
    while result and result[-1] in "-.":
        result.pop()

        if version < 262:
            break

    return "".join(result)


def read_static_hostname(module, version):
    """Read the static hostname as systemd's read_etc_hostname() does, an unusable one reading as unset."""
    try:
        # systemd-hostnamed 246 and later ignore a file they cannot read, such as one with a line too long, and earlier
        # ones fail to start
        with open(HOSTNAME_FILE, "rb") as handle:
            for line in read_lines(handle, version):
                if line is None:
                    return ""

                line = line.strip(ENV_WHITESPACE)

                if line and not line.startswith("#"):
                    hostname = hostname_cleanup(line, version)

                    # systemd 239 accepts any hostname left after the cleanup, such as one with '_'
                    if version < HOSTNAME_LDH_VERSION:
                        return hostname

                    # newer systemd accepts '?' wildcards and '$' tokens in a stored hostname, unlike this module
                    return hostname if hostname_valid(hostname.replace("?", "0").replace("$", "0"), version) else ""
    except PermissionError as error:
        # systemd-hostnamed runs as root, so it reads a file the module may not
        module.fail_json(msg=f"unable to read {HOSTNAME_FILE}: {error}")
    except OSError:
        # such as a missing file, a symbolic link loop or an I/O error
        return ""

    return ""


def ensure_present(module):
    # dasbus cannot send a surrogate and GLib cuts a string at a NUL, which would write a shortened value
    check_utf8(module, [(param, module.params[param]) for param in STRING_SETTINGS], noncharacters=False)

    # systemd-hostnamed 258 and later replace each '?' and 262 and later each '$' token in a transient hostname, so the
    # hostname it then reports would never match the option
    transient = module.params["transient_hostname"]
    if transient and ("?" in transient or "$" in transient):
        module.fail_json(
            msg=f"invalid transient_hostname {transient!r}: '?' wildcards and '$' tokens are not supported"
        )

    if module.check_mode and not HAS_DASBUS:
        module.exit_json(
            changed=any(
                module.params[param] is not None
                for param in [setting[0] for setting in SETTINGS] + ["transient_hostname"]
            ),
            hostname={},
        )

    proxy = systemd_proxy(module, "hostname1")

    current = systemd_properties(module, proxy, HOSTNAME_PROPERTIES)
    stored = {}
    machine_info_error = None
    compare_machine_info = any(module.params[param] is not None for param in MACHINE_INFO_KEYS.values())
    compare_static_hostname = module.params["static_hostname"] is not None

    version = None

    # the files are read as the running systemd reads them, which changes between versions
    if compare_machine_info or compare_static_hostname:
        version = systemd_version(module)

    if compare_machine_info:
        stored, machine_info_error = read_machine_info(module, version)

    if compare_static_hostname:
        stored["static_hostname"] = read_static_hostname(module, version)

    default = current["default_hostname"] or ""
    predicted = dict(current)
    pending = []

    for param, method in SETTINGS:
        value = module.params[param]
        if value is None:
            continue

        if stored[param] == value:
            continue

        if machine_info_error and param in MACHINE_INFO_KEYS.values():
            module.fail_json(
                msg=f"unable to set {param}: {MACHINE_INFO} {machine_info_error}, which systemd-hostnamed refuses to rewrite"
            )

        # this never converges, so it is refused also for the first request
        if (
            param in QUOTED_SETTINGS
            and ENV_QUOTE_ESCAPE_VERSION <= version < ENV_SHELL_ESCAPE_VERSION
            and SHELL_ESCAPED.intersection(value)
        ):
            module.fail_json(
                msg=f"invalid {param} {value!r}: systemd {version} reads '$', '`' and '\\' back from {MACHINE_INFO} "
                "with an added backslash, so the setting would never match"
            )

        # systemd 247 and earlier keep the hostname in effect in place of a static one naming the local host, and report
        # no HostnameSource
        if param == "static_hostname":
            predicted["hostname"] = value if static_takes_precedence(value, version) else default or current["hostname"]

            if current["hostname_source"] is not None:
                predicted["hostname_source"] = "static" if value else "default"

        predicted[param] = value
        pending.append((param, method, (value, False)))

    if transient and predicted["hostname"] != transient:
        # whether a static hostname takes precedence depends on the running systemd
        if predicted["static_hostname"] and version is None:
            version = systemd_version(module)

        if static_takes_precedence(predicted["static_hostname"], version):
            module.fail_json(
                msg=f"unable to set the transient hostname: the static hostname {predicted['static_hostname']} takes precedence"
            )

        predicted["hostname"] = transient

        if current["hostname_source"] is not None:
            predicted["hostname_source"] = "transient"

        pending.append(("transient_hostname", "SetHostname", (transient, False)))

    if transient == "":
        if current["hostname_source"] is None:
            module.fail_json(
                msg="unable to clear the transient hostname: HostnameSource is not supported by this version of systemd"
            )

        cleared = current["static_hostname"] and not predicted["static_hostname"]
        # SetStaticHostname already applies the static hostname, else the default, in place of a transient one
        static_pending = any(param == "static_hostname" for param, _method, _args in pending)

        if current["hostname_source"] == "transient" or cleared:
            predicted["hostname"] = predicted["static_hostname"] or default or current["hostname"]
            predicted["hostname_source"] = "static" if predicted["static_hostname"] else "default"

            if not static_pending:
                pending.append(("transient_hostname", "SetHostname", ("", False)))

    # the first request is validated by systemd-hostnamed before anything is written, a later one only after the
    # earlier requests are applied; a later request follows a setting compared against its file, so version is known
    for param, _method, args in pending[1:]:
        check_setting(module, param, args[0], version)

    if not pending:
        module.exit_json(changed=False, hostname=current)

    if module.check_mode:
        module.exit_json(changed=True, hostname=predicted)

    failed_result = {}

    for _param, method, args in pending:
        systemd_call(module, proxy, method, *args, failed_result=failed_result)
        # a later failure leaves this request applied
        failed_result = {"changed": True, "hostname": {}}

    current = systemd_properties(module, proxy, HOSTNAME_PROPERTIES, failed_result=failed_result)

    module.exit_json(changed=True, hostname=current)


def main():
    argument_spec = {
        "chassis": {
            "type": "str",
            "choices": [
                "",
                "container",
                "convertible",
                "desktop",
                "embedded",
                "handset",
                "laptop",
                "server",
                "tablet",
                "vm",
                "watch",
            ],
        },
        "deployment": {"type": "str"},
        "icon_name": {"type": "str"},
        "location": {"type": "str"},
        "pretty_hostname": {"type": "str"},
        "static_hostname": {"type": "str"},
        "transient_hostname": {"type": "str"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
