# git

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Clone git repositories

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    git_become: false
    git_become_user: root
    git_packages:
      - git
    git_repositories: []

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.git
          git_become: true
          git_become_user: linuxhq
          git_repositories:
            - repo: https://github.com/linuxhq/ansible-collection-linux.git
              dest: /home/linuxhq/git/linuxhq.linux

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
