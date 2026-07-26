# selinux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Security-Enhanced Linux

## Requirements

None

## Role Variables

    selinux_conf: /etc/selinux/config
    selinux_packages:
      - python3-libselinux
      - selinux-policy
    selinux_policy: targeted
    selinux_reboot: false
    selinux_reboot_timeout: 600
    selinux_state: enforcing
    selinux_update_kernel_param: false

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.selinux
          selinux_state: disabled
          selinux_reboot: true
