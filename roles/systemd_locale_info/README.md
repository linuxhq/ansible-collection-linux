# systemd\_locale\_info

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Gather information about the systemd locale and keyboard settings

## Requirements

* [systemd-localed](https://www.freedesktop.org/software/systemd/man/latest/systemd-localed.service.html)

## Role Variables

    systemd_locale_info_packages:
      - python3-dasbus

## Dependencies

None

## Return Values

    _systemd_locale_info_dict

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.systemd_locale_info
