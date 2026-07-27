# systemd\_timedate

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage the systemd time and date settings

## Requirements

* [systemd-timedated](https://www.freedesktop.org/software/systemd/man/latest/systemd-timedated.service.html)

## Role Variables

    systemd_timedate_adjust_system_clock: null
    systemd_timedate_local_rtc: null
    systemd_timedate_ntp: null
    systemd_timedate_packages:
      - python3-dasbus
    systemd_timedate_time: null
    systemd_timedate_timezone: null

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_timedate
          systemd_timedate_local_rtc: false
          systemd_timedate_ntp: true
          systemd_timedate_timezone: America/Los_Angeles
