# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_hostname
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
short_description: Manage the systemd hostname
description:
  - Manage the hostname settings owned by C(systemd-hostnamed), the same ones
    C(hostnamectl set-*) writes, by calling the C(org.freedesktop.hostname1)
    interface on the system bus directly.
  - Settings are compared against the current properties and only the ones that
    differ are written, options left unset are not touched.
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
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  icon_name:
    description:
      - Icon name of the machine, following the XDG icon naming specification.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  location:
    description:
      - Physical location of the machine, such as a rack or room name.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  pretty_hostname:
    description:
      - Free-form UTF-8 hostname for presentation, such as V(Taylor's Laptop), as
        C(hostnamectl hostname --pretty) sets.
      - Written to C(/etc/machine-info).
      - An empty string removes it from C(/etc/machine-info).
    type: str
  static_hostname:
    description:
      - Static hostname written to C(/etc/hostname), as
        C(hostnamectl hostname --static) sets.
      - C(systemd-hostnamed) applies it as the transient hostname as well, so
        RV(hostname) follows it.
      - An empty string removes C(/etc/hostname).
    type: str
  transient_hostname:
    description:
      - Transient hostname, as C(hostnamectl hostname --transient) sets.
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

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    HOSTNAME_PROPERTIES,
    systemd_call,
    systemd_properties,
    systemd_proxy,
)

SETTINGS = [
    ("chassis", "SetChassis"),
    ("deployment", "SetDeployment"),
    ("icon_name", "SetIconName"),
    ("location", "SetLocation"),
    ("pretty_hostname", "SetPrettyHostname"),
    ("static_hostname", "SetStaticHostname"),
]


def ensure_present(module):
    if module.check_mode and not HAS_DASBUS:
        module.exit_json(
            changed=any(
                module.params[param] is not None
                for param in [setting[0] for setting in SETTINGS]
                + ["transient_hostname"]
            ),
            hostname={},
        )

    proxy = systemd_proxy(module, "hostname1")

    current = systemd_properties(module, proxy, HOSTNAME_PROPERTIES)
    default = current["default_hostname"] or ""
    predicted = dict(current)
    pending = []

    for param, method in SETTINGS:
        value = module.params[param]
        if value is None or current[param] == value:
            continue

        predicted[param] = value
        if param == "static_hostname":
            predicted["hostname"] = value or default or current["hostname"]

        pending.append((method, (value, False)))

    transient = module.params["transient_hostname"]

    if transient and predicted["hostname"] != transient:
        if predicted["static_hostname"]:
            module.fail_json(
                msg="unable to set the transient hostname: the static hostname "
                f"{predicted['static_hostname']} takes precedence"
            )

        predicted["hostname"] = transient
        pending.append(("SetHostname", (transient, False)))

    if transient == "":
        if current["hostname_source"] is None:
            module.fail_json(
                msg="unable to clear the transient hostname: HostnameSource is not "
                "supported by this version of systemd"
            )

        cleared = current["static_hostname"] and not predicted["static_hostname"]

        if current["hostname_source"] == "transient" or cleared:
            predicted["hostname"] = default or current["hostname"]
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
