# rpmfusion

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Merger of Dribble, Freshrpms, and Livna

## Requirements

* [Extra Packages for Enterprise Linux](https://docs.fedoraproject.org/en-US/epel/)

## Role Variables

    rpmfusion_packages: []
    rpmfusion_repositories:
      - name: rpmfusion-free-updates
        state: enabled
      - name: rpmfusion-nonfree-updates
        state: enabled

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rpmfusion
          rpmfusion_packages:
            - kmod-VirtualBox
          rpmfusion_repositories:
            - name: rpmfusion-free-updates
              state: enabled
            - name: rpmfusion-free-updates-source
              state: enabled
            - name: rpmfusion-nonfree-updates
              state: enabled
            - name: rpmfusion-nonfree-updates-source
              state: enabled

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
