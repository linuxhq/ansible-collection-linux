# systemd\_timedate\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about the systemd time and date settings

## Requirements

* [systemd-timedated](https://www.freedesktop.org/software/systemd/man/latest/systemd-timedated.service.html)

## Role Variables

    systemd_timedate_info_packages:
      - python3-dasbus

## Dependencies

None

## Return Values

    _systemd_timedate_info_dict
    _systemd_timedate_info_list

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.systemd_timedate_info
