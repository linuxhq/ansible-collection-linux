# filesystem

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Makes a filesystem

## Requirements

None

## Role Variables

    filesystem_list: []
    filesystem_packages:
      - e2fsprogs
      - xfsprogs

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.filesystem
          filesystem_list:
            - dev: /dev/sdb1
              fstype: ext4

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
