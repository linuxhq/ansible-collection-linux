# selinux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Security-Enhanced Linux

## Requirements

None

## Role Variables

    selinux_booleans: []
    selinux_conf: /etc/selinux/config
    selinux_fcontexts: []
    selinux_packages:
      - python3-libselinux
      - python3-libsemanage
      - python3-policycoreutils
      - selinux-policy
    selinux_policy: targeted
    selinux_reboot: false
    selinux_reboot_timeout: 600
    selinux_restorecon: []
    selinux_state: enforcing
    selinux_update_kernel_param: false

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.selinux
          selinux_booleans:
            - name: container_use_devices
              state: true
          selinux_fcontexts:
            - target: '/srv(/.*)?'
              setype: container_file_t
          selinux_reboot: true
          selinux_restorecon:
            - /srv
          selinux_state: enforcing
