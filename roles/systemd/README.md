# systemd

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A system and service manager for Linux

## Requirements

None

## Role Variables

    systemd_journald: {}
    systemd_logind: {}
    systemd_system: {}
    systemd_user: {}

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd
          systemd_journald:
            Audit:
            Compress: true
          systemd_logind:
            KillOnlyUsers:
              - vagrant
          systemd_system:
            CrashReboot: false
          systemd_user:
            LogColor: true
            LogTime: false
