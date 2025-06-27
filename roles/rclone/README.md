# rclone

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A command-line program to manage files on cloud storage

## Requirements

None

## Role Variables

    rclone_arch: amd64
    rclone_conf: {}
    rclone_mounts: []
    rclone_no_log: false
    rclone_profile: {}
    rclone_sysconfig: {}
    rclone_version: v1.69.3

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rclone
          rclone_conf:
            koofr:
              password: "{{ lookup('env', 'KOOFR_PASSWORD') }}"
              provider: koofr
              type: koofr
              user: "{{ lookup('env', 'KOOFR_USERNAME') }}"
            koofr-crypt:
              password: "{{ lookup('env', 'KOOFR_CRYPT_PASSWORD') }}"
              password2: "{{ lookup('env', 'KOOFR_CRYPT_PASSWORD2') }}"
              remote: koofr:/rclone
              type: crypt
          rclone_mounts:
            - name: rclone-koofr-ro
              remote: 'koofr-crypt:'
              mountpoint: /mnt/koofr
              flags:
                - --read-only
                - --vfs-cache-mode=full
          rclone_sysconfig:
            rclone_verbose: '1'

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
