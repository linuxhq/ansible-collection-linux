# rclone

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A command-line program to manage files on cloud storage

## Requirements

None

## Role Variables

    rclone_config: []
    rclone_config_pass: null
    rclone_no_log: false
    rclone_user: root

## Dependencies

* [epel](../epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rclone
          rclone_config:
            - name: molecule
              type: http
              url: https://downloads.rclone.org
          rclone_config_pass: "{{ vault_rclone_config_pass }}"
          rclone_user: vagrant
