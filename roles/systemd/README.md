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
