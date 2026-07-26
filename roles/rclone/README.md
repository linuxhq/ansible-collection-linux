# rclone

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A command-line program to manage files on cloud storage

## Requirements

None

## Role Variables

    rclone_config: []
    rclone_config_pass: null
    rclone_config_path: /etc/rclone/rclone.conf
    rclone_mounts: []
    rclone_no_log: false
    rclone_profile: {}
    rclone_sysconfig: {}

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rclone
          rclone_config:
            - name: source
              type: local
              nounc: true

            - name: backup
              type: alias
              remote: source:/srv

            - name: secret
              type: crypt
              remote: source:/srv/rclone
              password: "{{ vault_rclone_crypt_pass | linuxhq.linux.rclone_obscure }}"

          rclone_config_pass: "{{ vault_rclone_config_pass }}"

          rclone_mounts:
            - name: rclone-backup
              remote: 'backup:'
              mountpoint: /mnt/backup
              flags:
                - --read-only

          rclone_profile:
            rclone_progress: true
            rclone_verbose: 1

          rclone_sysconfig:
            rclone_allow_other: true
            rclone_read_only: true
