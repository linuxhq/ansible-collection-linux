# cronie

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Cron daemon for executing programs at set times

## Requirements

None

## Role Variables

    cronie_allow: []
    cronie_args: []
    cronie_deny: []
    cronie_jobs: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.cronie
          cronie_allow:
            - vagrant
          cronie_deny:
            - vagrant
          cronie_jobs:
            - cron_file: ansible
              jobs:
                - name: Create temporary file
                  minute: '*/1'
                  job: echo 1 > /tmp/cronie
                  user: root
