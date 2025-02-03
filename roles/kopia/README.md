# kopia

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Fast and secure open-source backup software

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    kopia_maintenance: []
    kopia_packages:
      - kopia
    kopia_password: kopia
    kopia_policies: []
    kopia_repository: {}
    kopia_rpm_key: 'https://kopia.io/signing-key'
    kopia_server: false
    kopia_server_args:
      - --address=127.0.0.1:51515
      - --disable-csrf-token-checks
      - --insecure
      - --no-check-for-updates
      - --without-password

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.kopia
          kopia_maintenance:
            - --enable-quick true
          kopia_policies:
            - target: /home/linuxhq/containers
              flags:
                - --compression gzip
                - --keep-annual 0
                - --keep-hourly 24
                - --keep-latest 2
                - --keep-monthly 3
                - --keep-weekly 4
                - --snapshot-interval 1h
          kopia_repository:
            location: s3
            flags:
              - "--access-key {{ aws_access_key_id }}"
              - "--bucket kopia-backups"
              - "--endpoint s3.us-west-1.amazonaws.com"
              - "--prefix {{ inventory_hostname }}/"
              - "--region us-west-1"
              - "--secret-access-key {{ aws_secret_access_key }}"
          kopia_server: true

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
