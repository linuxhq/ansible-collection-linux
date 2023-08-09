# ius

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Inline with Upstream Stable

## Requirements

* [Extra Packages for Enterprise Linux](https://docs.fedoraproject.org/en-US/epel/)

## Role Variables

Available variables are listed below, along with default values:

    ius_packages: []
    ius_release: https://repo.ius.io/ius-release-el7.rpm
    ius_repository_ius: true
    ius_repository_ius_debuginfo: false
    ius_repository_ius_source: false
    ius_repository_ius_archive: false
    ius_repository_ius_archive_debuginfo: false
    ius_repository_ius_archive_source: false
    ius_repository_ius_testing: false
    ius_repository_ius_testing_debuginfo: false
    ius_repository_ius_testing_source: false

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.ius
          ius_packages:
            - tmux2
          ius_repository_ius_testing: true

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
