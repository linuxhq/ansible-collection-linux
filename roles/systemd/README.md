# systemd

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A system and service manager for Linux

## Requirements

None

## Role Variables

    systemd_hostnamectl: {}
    systemd_journald: {}
    systemd_localectl: {}
    systemd_logind: {}
    systemd_system: {}
    systemd_timedatectl: {}
    systemd_user: {}

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd
          systemd_hostnamectl:
            set-deployment: production
            set-hostname: "{{ inventory_hostname }}"
            set-icon-name: computer-server
          systemd_journald:
            Audit:
            Compress: true
          systemd_localectl:
            set-locale: LANG=en_US.UTF-8
          systemd_logind:
            KillOnlyUsers:
              - vagrant
          systemd_system:
            CrashReboot: false
          systemd_timedatectl:
            set-local-rtc: '0'
            set-ntp: '1'
            set-timezone: America/Los_Angeles
          systemd_user:
            LogColor: true
            LogTime: false

## License

Copyright (c) Linux HeadQuarters

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
