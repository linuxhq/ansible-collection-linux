# docker\_network

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage docker networks

## Requirements

* [docker](https://www.docker.com)

## Role Variables

    docker_network_list: []

## Dependencies

* [linuxhq.linux.docker](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/docker)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.docker_network
          docker_network_list:
            - name: linuxhq
              ipam_config:
                - subnet: 192.168.0.0/24
