# podman\_quadlet

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Allows users to manage quadlets

## Requirements

* [podman](https://podman.io)

## Role Variables

    podman_quadlet_containers: []
    podman_quadlet_networks: []
    podman_quadlet_no_log: false
    podman_quadlet_secrets: []
    podman_quadlet_user: null
    podman_quadlet_volumes: []

## Dependencies

* [podman](../podman)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.podman_quadlet
          podman_quadlet_containers:
            - name: alpine
              unit:
                Unit:
                  PartOf: podman-quadlet.target
                Container:
                  ContainerName: alpine
                  Environment:
                    COUNTRY: United States
                  Exec: sleep infinity
                  Image: docker.io/library/alpine:latest
                  Network: molecule.network
                  Secret:
                    - molecule,type=env,target=MOLECULE_SECRET
                  Volume: molecule.volume:/data
                Service:
                  Restart: always
                Install:
                  WantedBy: podman-quadlet.target
          podman_quadlet_networks:
            - name: molecule
              unit:
                Network:
                  NetworkName: molecule
                  Subnet: 192.168.0.0/24
          podman_quadlet_secrets:
            - name: molecule
              data: molecule
          podman_quadlet_user: vagrant
          podman_quadlet_volumes:
            - name: molecule
              unit:
                Volume:
                  VolumeName: molecule
