# podman

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Podman container engine

## Requirements

None

## Role Variables

    podman_packages:
      - podman
    podman_systemd:
      - podman-auto-update.timer

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.podman
          podman_packages:
            - podman
            - systemd-container
