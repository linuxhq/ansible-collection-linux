#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_hostname_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.4.0"
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
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when dasbus is unavailable.
  diff_mode:
    description: Diff mode is not supported.
    support: none
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
    - Empty when dasbus is unavailable in check mode.
  returned: always
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
