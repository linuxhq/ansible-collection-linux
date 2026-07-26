# docker\_compose

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Run multi-container applications with Docker

## Requirements

* [docker](https://www.docker.com)

## Role Variables

    docker_compose_bin: /usr/libexec/docker/cli-plugins/docker-compose
    docker_compose_dir: /etc/docker/compose
    docker_compose_packages:
      - docker-compose-plugin
    docker_compose_projects: []

## Dependencies

* [linuxhq.linux.docker](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/docker)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.docker_compose
          docker_compose_projects:
            - name: linuxhq
              env:
                LINUXHQ_TZ: America/Los_Angeles
                LINUXHQ_UMASK: 2
                LINUXHQ_WATCHTOWER_CLEANUP: 'true'
                LINUXHQ_WATCHTOWER_POLL_INTERVAL: 3600
              networks:
                watchtower:
                  driver: bridge
                  ipam:
                    config:
                      - subnet: 192.168.0.0/24
              services:
                watchtower:
                  container_name: watchtower
                  environment:
                    WATCHTOWER_CLEANUP: ${LINUXHQ_WATCHTOWER_CLEANUP}
                    WATCHTOWER_POLL_INTERVAL: ${LINUXHQ_WATCHTOWER_POLL_INTERVAL}
                    TZ: ${LINUXHQ_TZ}
                    UMASK: ${LINUXHQ_UMASK}
                  image: containrrr/watchtower:latest
                  networks:
                    - watchtower
                  volumes:
                    - /var/run/docker.sock:/var/run/docker.sock
