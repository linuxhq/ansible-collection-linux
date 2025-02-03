# chrony

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Programs for keeping computer clocks accurate

## Requirements

None

## Role Variables

    chrony_conf:
      - driftfile /var/lib/chrony/drift
      - keyfile /etc/chrony.keys
      - leapsectz right/UTC
      - logdir /var/log/chrony
      - makestep 1.0 3
      - ntsdumpdir /var/lib/chrony
      - pool 1.pool.ntp.org iburst
      - pool 2.pool.ntp.org iburst
      - pool 3.pool.ntp.org iburst
      - rtcsync
      - sourcedir /run/chrony-dhcp
    chrony_options: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.chrony
          chrony_conf:
            - authselectmode require
            - cmdport 0
            - driftfile /var/lib/chrony/drift
            - hwtimestamp *
            - log measurements statistics tracking
            - logdir /var/log/chrony
            - makestep 1.0 3
            - minsources 2
            - ntsdumpdir /var/lib/chrony
            - rtcsync
            - server ntppool1.time.nl iburst nts
            - server ntppool2.time.nl iburst nts
            - sourcedir /run/chrony-dhcp
          chrony_options:
            - '-F 1'

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
