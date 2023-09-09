# pam\_limit

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

PAM module to limit resources

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    pam_limits: []
    pam_limits_d: []

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.pam_limit
          pam_limits:
            - domain: '*'
              limit_item: core
              limit_type: hard
              value: 0
            - domain: '*'
              limit_item: nofile
              limit_type: hard
              value: 39693561
          pam_limits_d:
            - file: 99-linuxhq
              limits:
                - domain: joe
                  limit_item: soft
                  limit_type: nofile
                  value: 64000
                - domain: smith
                  limit_type: hard
                  limit_item: fsize
                  value: 1000000

## License

Copyright (C) 2023 Linux HeadQuarters

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
