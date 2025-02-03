# rpmfusion

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Merger of Dribble, Freshrpms, and Livna

## Requirements

* [Extra Packages for Enterprise Linux](https://docs.fedoraproject.org/en-US/epel/)

## Role Variables

Available variables are listed below, along with default values:

    rpmfusion_packages: []
    rpmfusion_releasever: "{{ ansible_distribution_major_version }}"
    rpmfusion_repository_free_updates: true
    rpmfusion_repository_free_updates_debuginfo: false
    rpmfusion_repository_free_updates_source: false
    rpmfusion_repository_free_updates_testing: false
    rpmfusion_repository_free_updates_testing_debuginfo: false
    rpmfusion_repository_free_updates_testing_source: false
    rpmfusion_repository_nonfree_updates: true
    rpmfusion_repository_nonfree_updates_debuginfo: false
    rpmfusion_repository_nonfree_updates_source: false
    rpmfusion_repository_nonfree_updates_testing: false
    rpmfusion_repository_nonfree_updates_testing_debuginfo: false
    rpmfusion_repository_nonfree_updates_testing_source: false

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rpmfusion
          rpmfusion_packages:
            - kmod-VirtualBox
          rpmfusion_repository_free_updates_source: true
          rpmfusion_repository_nonfree_updates_source: true

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
