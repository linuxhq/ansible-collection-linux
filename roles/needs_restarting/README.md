# needs\_restarting

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF needs-restarting Plugin

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    nr_crontab: null
    nr_package_dir: /etc/dnf/plugins/needs-restarting.d/
    nr_packages: []
    nr_user: root

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.needs_restarting
          nr_crontab: '0 8 * * 1'
          nr_packages:
            - kernel-lt
            - kernel-ml

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
