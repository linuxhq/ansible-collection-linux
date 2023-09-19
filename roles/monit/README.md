# monit

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Utility for monitoring services on a Unix system

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    monit_alert:
      - name: root@localhost
    monit_daemon: 30
    monit_eventqueue_basedir: /tmp
    monit_eventqueue_slots: 1024
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
    monit_program: []
    monit_start_delay: 0

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.monit
          monit_alert:
            - name: monit@linuxhq.net
              rules:
                - not on { instance, action }
          monit_daemon: 60
          monit_eventqueue_basedir: /var/tmp
          monit_eventqueue_slots: 2048
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

## License

Copyright (C) 2023 Linux HeadQuarters

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
