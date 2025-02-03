# docker

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Docker Community Edition

## Requirements

None

## Role Variables

    docker_daemon: {}
    docker_packages:
      - containerd.io
      - docker-ce
    docker_repository_stable: true
    docker_repository_stable_debuginfo: false
    docker_repository_stable_source: false
    docker_repository_test: false
    docker_repository_test_debuginfo: false
    docker_repository_test_source: false
    docker_repository_nightly: false
    docker_repository_nightly_debuginfo: false
    docker_repository_nightly_source: false
    docker_systemd:
      - containerd.service
      - docker.service
    docker_users: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.docker
          docker_users:
            - linuxhq

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
