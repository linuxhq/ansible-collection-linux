# systemd\_hostname

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage the systemd hostname

## Requirements

* [systemd-hostnamed](https://www.freedesktop.org/software/systemd/man/latest/systemd-hostnamed.service.html)

## Role Variables

    systemd_hostname_chassis: null
    systemd_hostname_deployment: null
    systemd_hostname_icon_name: null
    systemd_hostname_location: null
    systemd_hostname_packages:
      - python3-dasbus
    systemd_hostname_pretty_hostname: null
    systemd_hostname_static_hostname: null
    systemd_hostname_transient_hostname: null

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_hostname
          systemd_hostname_chassis: server
          systemd_hostname_deployment: production
          systemd_hostname_icon_name: computer-server
          systemd_hostname_location: rack 4
          systemd_hostname_pretty_hostname: Example Server
          systemd_hostname_static_hostname: server.example.com
