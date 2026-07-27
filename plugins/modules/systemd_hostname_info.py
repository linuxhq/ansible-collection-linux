# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_hostname_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
short_description: Gather the systemd hostname settings
description:
  - Gather the hostname, machine information and kernel identity reported by
    C(systemd-hostnamed), the same data C(hostnamectl status) prints, from the
    C(org.freedesktop.hostname1) interface on the system bus.
notes:
  - Requires a running C(systemd-hostnamed) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
requirements:
  - dasbus
"""

EXAMPLES = r"""
- name: Ensure the hostname settings are gathered
  linuxhq.linux.systemd_hostname_info:
  register: __systemd_hostname_query
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
    systemd_properties,
    systemd_proxy,
)


def info(module):
    if module.check_mode and not HAS_DASBUS:
        module.exit_json(changed=False, hostname={})

    proxy = systemd_proxy(module, "hostname1")

    hostname = systemd_properties(module, proxy, HOSTNAME_PROPERTIES)

    module.exit_json(changed=False, hostname=hostname)


def main():
    module = AnsibleModule(
        argument_spec={},
        supports_check_mode=True,
    )

    info(module)


if __name__ == "__main__":
    main()
