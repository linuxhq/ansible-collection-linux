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
    missing file means no setting is stored.
  - O(static_hostname) is compared against the static hostname reported by
    C(systemd-hostnamed).
  - Every option is validated before any setting is written, so an invalid
    value fails without leaving earlier settings applied.
  - With no options set the module reads the current settings and reports no
    change.
notes:
  - Requires a running C(systemd-hostnamed) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
options:
  chassis:
    description:
      - Chassis type of the machine.
      - Written to C(/etc/machine-info).
    type: str
    choices:
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
      - Must be a valid file name, so it cannot contain V(/) or control
        characters and cannot be V(.) or V(..).
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  location:
    description:
      - Physical location of the machine, such as a rack or room name.
      - Control characters are not allowed.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  pretty_hostname:
    description:
      - Free-form UTF-8 hostname for presentation, such as V(Taylor's Laptop), as
        C(hostnamectl hostname --pretty) sets.
      - Control characters are not allowed.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  static_hostname:
    description:
      - Static hostname written to C(/etc/hostname), as
        C(hostnamectl hostname --static) sets.
      - C(systemd-hostnamed) applies it as the transient hostname as well, so
        RV(hostname) follows it.
      - Must be a valid hostname of at most 64 characters, made of labels of
        letters, digits and V(-) separated by V(.), where no label is empty or
        starts or ends with V(-).
      - Each V(?) is a wildcard that systemd 258 and later replace with a
        hexadecimal character derived from the machine ID. A static hostname
        reported with a lowercase hexadecimal character in place of each V(?)
        matches, so it is not rewritten. In check mode the predicted
        RV(hostname) keeps the V(?) characters.
      - An empty string removes C(/etc/hostname).
    type: str
  transient_hostname:
    description:
      - Transient hostname, as C(hostnamectl hostname --transient) sets.
      - Must be a valid hostname, following the same rules as
        O(static_hostname) without the V(?) wildcard.
      - C(/etc/hostname) takes the highest preference in C(systemd-hostnamed), so
        a transient hostname cannot take effect while a static one is configured.
      - Nothing is done when RV(hostname) already matches, whatever the source.
        When it differs and a static hostname is configured, this fails rather
        than reporting a change it cannot make, so set O(static_hostname) to the
        same value instead, either on its own or alongside.
      - An empty string resets it to the default hostname. While a static
        hostname is in effect there is nothing observable to reset, so it is
        reported as no change.
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
  returned: always
  type: dict
  sample:
    boot_id: 8d1e0f2a4b6c8d0e1f2a3b4c5d6e7f80
    chassis: server
    chassis_asset_tag: null
    default_hostname: localhost
    deployment: production
    firmware_date: 1735689600000000
    firmware_vendor: Dell Inc.
    firmware_version: 2.19.0
    hardware_model: PowerEdge R640
    hardware_sku: null
    hardware_vendor: Dell Inc.
    hardware_version: null
    home_url: https://www.redhat.com/
    hostname: server.example.com
    hostname_source: static
    icon_name: computer-server
    kernel_name: Linux
    kernel_release: 5.14.0-570.el9.x86_64
    kernel_version: '#1 SMP PREEMPT_DYNAMIC'
    location: rack 4
    machine_id: 3f0a1b2c3d4e5f60718293a4b5c6d7e8
    operating_system_cpe_name: cpe:/o:redhat:enterprise_linux:9::baseos
    operating_system_fancy_name: null
    operating_system_image_id: null
    operating_system_image_version: null
    operating_system_pretty_name: Red Hat Enterprise Linux 9.6 (Plow)
    operating_system_support_end: 1904169600000000
    pretty_hostname: Example Server
    static_hostname: server.example.com
    vsock_cid: null
    tags:
      - production
      - web
"""

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    HOSTNAME_PROPERTIES,
    systemd_call,
    systemd_properties,
    systemd_proxy,
)

MACHINE_INFO = "/etc/machine-info"

MACHINE_INFO_KEYS = {
    "CHASSIS": "chassis",
    "DEPLOYMENT": "deployment",
    "ICON_NAME": "icon_name",
    "LOCATION": "location",
    "PRETTY_HOSTNAME": "pretty_hostname",
}

SETTINGS = [
    ("chassis", "SetChassis"),
    ("deployment", "SetDeployment"),
    ("icon_name", "SetIconName"),
    ("location", "SetLocation"),
    ("pretty_hostname", "SetPrettyHostname"),
    ("static_hostname", "SetStaticHostname"),
]

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
DEPLOYMENT = re.compile(r"[A-Za-z0-9.:-]+\Z")
HOSTNAME_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
HOSTNAME = re.compile(rf"{HOSTNAME_LABEL}(?:\.{HOSTNAME_LABEL})*\Z")
HOSTNAME_MAX = 64
HOSTNAME_WILDCARD_CHARACTERS = "0123456789abcdef"
NAME_MAX = 255


def hostname_valid(value):
    return len(value) <= HOSTNAME_MAX and HOSTNAME.match(value) is not None


def icon_name_valid(value):
    return (
        value not in (".", "..")
        and "/" not in value
        and len(value.encode("utf-8")) <= NAME_MAX
        and not CONTROL_CHARACTERS.search(value)
    )


def validate_settings(module):
    params = module.params

    for param in ("location", "pretty_hostname"):
        if params[param] and CONTROL_CHARACTERS.search(params[param]):
            module.fail_json(msg=f"invalid {param}: control characters are not allowed")

    if params["deployment"] and not DEPLOYMENT.match(params["deployment"]):
        module.fail_json(
            msg=f"invalid deployment {params['deployment']!r}: only letters, digits, '-', '.' and ':' are allowed"
        )

    if params["icon_name"] and not icon_name_valid(params["icon_name"]):
        module.fail_json(msg=f"invalid icon_name {params['icon_name']!r}: it must be a valid file name")

    if params["static_hostname"] and not hostname_valid(params["static_hostname"].replace("?", "0")):
        module.fail_json(msg=f"invalid static_hostname {params['static_hostname']!r}: it is not a valid hostname")

    if params["transient_hostname"] and not hostname_valid(params["transient_hostname"]):
        module.fail_json(msg=f"invalid transient_hostname {params['transient_hostname']!r}: it is not a valid hostname")


def machine_info_value(text):
    characters = iter(text.lstrip())
    value = []
    keep = 0
    quote = None

    for character in characters:
        if quote is None and character in "\"'":
            quote = character
            continue

        if character == quote:
            quote = None
            continue

        if character == "\\" and quote != "'":
            escaped = next(characters, "")
            if quote == '"' and escaped not in '"\\`$':
                value.append("\\")

            character = escaped
        elif quote is None and character.isspace():
            value.append(character)
            continue

        value.append(character)
        keep = len(value)

    return "".join(value[:keep])


def read_machine_info(module):
    values = dict.fromkeys(MACHINE_INFO_KEYS.values(), "")

    try:
        with open(MACHINE_INFO, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        return values
    except OSError as error:
        module.fail_json(msg=f"unable to read {MACHINE_INFO}: {to_native(error)}")

    for line in lines:
        key, separator, value = line.strip().partition("=")
        param = MACHINE_INFO_KEYS.get(key.strip())

        if separator and param:
            values[param] = machine_info_value(value)

    return values


def hostname_matches(current, desired):
    current = current or ""

    if len(current) != len(desired):
        return False

    return all(
        actual == wanted or (wanted == "?" and actual in HOSTNAME_WILDCARD_CHARACTERS)
        for actual, wanted in zip(current, desired)
    )


def ensure_present(module):
    validate_settings(module)

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
    if any(module.params[param] is not None for param in MACHINE_INFO_KEYS.values()):
        stored = read_machine_info(module)

    default = current["default_hostname"] or ""
    predicted = dict(current)
    pending = []

    for param, method in SETTINGS:
        value = module.params[param]
        if value is None:
            continue

        if param == "static_hostname":
            if hostname_matches(current[param], value):
                continue

            predicted["hostname"] = value or default or current["hostname"]
            predicted["hostname_source"] = "static" if value else "default"
        elif stored[param] == value:
            continue

        predicted[param] = value
        pending.append((method, (value, False)))

    transient = module.params["transient_hostname"]

    if transient and predicted["hostname"] != transient:
        if predicted["static_hostname"]:
            module.fail_json(
                msg=f"unable to set the transient hostname: the static hostname {predicted['static_hostname']} takes precedence"
            )

        predicted["hostname"] = transient
        predicted["hostname_source"] = "transient"
        pending.append(("SetHostname", (transient, False)))

    if transient == "":
        if current["hostname_source"] is None:
            module.fail_json(
                msg="unable to clear the transient hostname: HostnameSource is not supported by this version of systemd"
            )

        cleared = current["static_hostname"] and not predicted["static_hostname"]

        if current["hostname_source"] == "transient" or cleared:
            predicted["hostname"] = predicted["static_hostname"] or default or current["hostname"]
            predicted["hostname_source"] = "static" if predicted["static_hostname"] else "default"
            pending.append(("SetHostname", ("", False)))

    if not pending:
        module.exit_json(changed=False, hostname=current)

    if module.check_mode:
        module.exit_json(changed=True, hostname=predicted)

    for method, args in pending:
        systemd_call(module, proxy, method, *args)

    current = systemd_properties(module, proxy, HOSTNAME_PROPERTIES)

    module.exit_json(changed=True, hostname=current)


def main():
    argument_spec = {
        "chassis": {
            "type": "str",
            "choices": [
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
