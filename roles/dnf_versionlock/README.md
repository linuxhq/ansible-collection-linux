# dnf\_versionlock

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF versionlock Plugin

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    dnf_versionlock_enabled: true
    dnf_versionlock_locklist: /etc/dnf/plugins/versionlock.list
    dnf_versionlock_packages: []

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.dnf_versionlock
          dnf_versionlock_packages:
            - name: docker-ce
              version: '3:25.0.5-1.el9.*'
            - name: docker-ce-cli
              version: '1:25.0.5-1.el9.*'
            - name: docker-ce-rootless-extras
              version: '0:25.0.5-1.el9.*'
            - name: containerd.io
              version: '0:1.6.28-3.2.el9.*'

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
