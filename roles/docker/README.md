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
    docker_repositories:
      - name: docker-ce-stable
        state: enabled
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
            - vagrant
