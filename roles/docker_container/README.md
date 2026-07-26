# docker\_container

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage docker containers

## Requirements

* [docker](https://www.docker.com)

## Role Variables

    docker_container_list: []

## Dependencies

* [linuxhq.linux.docker](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/docker)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.docker_container
          docker_container_list:
            - name: linuxhq
              image: nginxinc/nginx-unprivileged:latest
