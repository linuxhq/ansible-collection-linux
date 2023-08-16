# elrepo

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

ELRepo Project

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    elrepo_kernel: false
    elrepo_kernel_absent:
      - kernel-devel
      - kernel-headers
      - kernel-tools
      - kernel-tools-libs
    elrepo_kernel_version: ml
    elrepo_packages: []
    elrepo_releasever: "{{ ansible_distribution_major_version }}"
    elrepo_repository_elrepo: true
    elrepo_repository_elrepo_testing: false
    elrepo_repository_elrepo_kernel: false
    elrepo_repository_elrepo_extras: false
    elrepo_rpm_key: https://www.elrepo.org/RPM-GPG-KEY-elrepo.org

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.elrepo
          elrepo_kernel: true
          elrepo_kernel_version: lt
          elrepo_packages:
            - kmod-a3818

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
