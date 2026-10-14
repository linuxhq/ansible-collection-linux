# rclone

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A command-line program to manage files on cloud storage

## Requirements

* [podman](https://podman.io)

## Role Variables

    rclone_config: []
    rclone_config_pass: null
    rclone_image: docker.io/rclone/rclone:latest
    rclone_mounts: []
    rclone_no_log: false

## Dependencies

* [epel](../epel)
* [podman](../podman)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rclone
          rclone_config:
            - name: molecule
              type: http
              url: https://downloads.rclone.org

          rclone_config_pass: "{{ vault_rclone_config_pass }}"

          rclone_mounts:
            - name: rclone-http
              remote: 'molecule:'
              mountpoint: /mnt/http
              environment:
                RCLONE_ALLOW_OTHER: true
                RCLONE_READ_ONLY: true
                RCLONE_VFS_CACHE_MODE: full
