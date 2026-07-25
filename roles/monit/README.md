# monit

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Utility for monitoring services on a Unix system

## Requirements

None

## Role Variables

    monit_alert: []
    monit_daemon: 30
    monit_eventqueue_basedir: /tmp
    monit_eventqueue_slots: 1024
    monit_exec: []
    monit_filesystem: []
    monit_httpd:
      - port 2812
      - use address localhost
      - allow localhost
      - allow admin:monit
    monit_httpd_ssl: {}
    monit_host: []
    monit_include: /etc/monit.d/*
    monit_log: syslog
    monit_mailformat:
      from: Monit <monit@$HOST>
      subject: monit alert -- $EVENT $SERVICE
      message: |-
        $EVENT Service $SERVICE
             Date:        $DATE
             Action:      $ACTION
             Host:        $HOST
             Description: $DESCRIPTION

        Your faithful employee,
        Monit
    monit_mailserver: localhost
    monit_process: []
    monit_program: []
    monit_start_delay: 0

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.monit
          monit_alert:
            - name: monit@linuxhq.net
              rules:
                - not on { instance, action }
          monit_daemon: 60
          monit_eventqueue_basedir: /var/tmp
          monit_eventqueue_slots: 2048
          monit_exec:
            - name: dev_null.sh
              base64: |
                IyEvYmluL2Jhc2gKCmVjaG8gMSA+IC9kZXYvbnVsbAo=
          monit_filesystem:
            - name: root
              rules:
                - path /
                - if space usage gt 80%
                - for 5 cycles then alert
          monit_host:
            - name: https
              rules:
                - address 127.0.0.1
                - if failed port 443
                - for 5 cycles then alert
          monit_program:
            - name: httpd
              rules:
                - path /usr/bin/systemctl --quiet is-active httpd.service
                - if status ne 0
                - for 5 cycles then alert
          monit_start_delay: 120
