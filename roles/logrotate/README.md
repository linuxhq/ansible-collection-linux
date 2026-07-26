# logrotate

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Rotates, compresses, and mails system logs

## Requirements

None

## Role Variables

    logrotate_conf:
      - weekly
      - rotate 4
      - create
      - dateext
      - include /etc/logrotate.d
    logrotate_d:
      - file: btmp
        logs:
          - path: /var/log/btmp
            options:
              - missingok
              - monthly
              - create 0660 root utmp
              - rotate 1
      - file: wtmp
        logs:
          - path: /var/log/wtmp
            options:
              - missingok
              - monthly
              - create 0664 root utmp
              - minsize 1M
              - rotate 1

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.logrotate
          logrorate_conf:
            - compress
            - create
            - daily
            - dateext
            - include /etc/logrotate.d
            - rotate 1
            - shred
          logrotate_d:
            - file: linuxhq
              logs:
                - path: /var/log/dnf.log
                  options:
                    - compress
                    - daily
                    - shred
