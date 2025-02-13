# needs\_restarting

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF needs-restarting Plugin

## Requirements

None

## Role Variables

    needs_restarting_crontab: null
    needs_restarting_package_dir: /etc/dnf/plugins/needs-restarting.d
    needs_restarting_package_list: []
    needs_restarting_user: root

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.needs_restarting
          needs_restarting_crontab: '0 8 * * 1'
          needs_restarting_package_list:
            - kernel-lt
            - kernel-ml

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
