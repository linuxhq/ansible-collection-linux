# epel

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Extra Packages for Enterprise Linux

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    epel_packages: []
    epel_releasever: "{{ ansible_distribution_major_version }}"
    epel_repository_epel: true
    epel_repository_epel_debuginfo: false
    epel_repository_epel_source: false
    epel_repository_testing: false
    epel_repository_testing_debuginfo: false
    epel_repository_testing_source: false

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.epel
          epel_repository_epel: true
          epel_repository_testing: true

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
