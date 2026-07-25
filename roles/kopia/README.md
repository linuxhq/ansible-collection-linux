# kopia

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Fast and secure open-source backup software

## Requirements

None

## Role Variables

    kopia_maintenance: []
    kopia_packages:
      - kopia
    kopia_password: kopia
    kopia_policies: []
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
            - target: /home/vagrant
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
              - "--access-key AKIATG524EM7GHSXQNUA"
              - "--bucket vagrant-kopia-backup"
              - "--endpoint s3.us-west-1.amazonaws.com"
              - "--prefix vagrant/"
              - "--region us-west-1"
              - "--secret-access-key 5D4Oa6QGInHvwBEWJwJoImmAjsQi2hO65+FfhGUK"
          kopia_server: true
