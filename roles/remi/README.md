# remi

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Remi's RPM repository

## Requirements

None

## Role Variables

    remi_baseurl: 'https://rpms.remirepo.net'
    remi_packages: []
    remi_release: "remi-release-{{ ansible_distribution_major_version }}.rpm"
    remi_repositories:
      - name: remi-modular
        state: enabled
      - name: remi-safe
        state: enabled

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.remi
          remi_packages:
            - @php:remi-8.5

## License

Copyright (c) Linux HeadQuarters

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
