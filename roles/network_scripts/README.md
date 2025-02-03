# network\_scripts

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of network scripts on a host

## Requirements

None

## Role Variables

    network: []
    network_scripts: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.network_scripts
          network:
            - key: forward_ipv4
              value: 'yes'
            - key: hostname
              value: "{{ inventory_hostname }}"
            - key: networking
              value: 'yes'
            - key: networking_ipv6
              value: 'no'
          network_scripts:
            - device: eno1
              settings:
                - key: bootproto
                  value: 'none'
                - key: defroute
                  value: 'yes'
                - key: gateway
                  value: 10.0.0.1
                - key: ipaddr
                  value: 10.0.0.2
                - key: prefix
                  value: 29

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
