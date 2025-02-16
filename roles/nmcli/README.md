# nmcli

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage networking

## Requirements

None

## Role Variables

    nmcli: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.nmcli
          nmcli:
            - conn_name: "{{ ansible_default_ipv4.interface }}"
              dns4:
                - "{{ ansible_lo.ipv4.address }}"
              ip4: "{{ ansible_default_ipv4.address }}/{{ ansible_default_ipv4.prefix }}"
              gw4: "{{ ansible_default_ipv4.gateway }}"
              type: ethernet
            - conn_name: enp36s0
              state: absent
            - conn_name: usb0
              state: absent

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
