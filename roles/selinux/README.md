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

## License

Copyright (C) 2025 Linux HeadQuarters

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
