# systemd\_locale

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage the systemd locale and keyboard settings

## Requirements

* [systemd-localed](https://www.freedesktop.org/software/systemd/man/latest/systemd-localed.service.html)

## Role Variables

    systemd_locale_locale: null
    systemd_locale_packages:
      - python3-dasbus
    systemd_locale_vconsole_keymap: null
    systemd_locale_vconsole_keymap_toggle: null
    systemd_locale_x11_layout: null
    systemd_locale_x11_model: null
    systemd_locale_x11_options: null
    systemd_locale_x11_variant: null

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_locale
          systemd_locale_locale:
            lang: en_US.UTF-8
            lc_time: en_DK.UTF-8

        - role: linuxhq.linux.systemd_locale
          systemd_locale_x11_layout: us
          systemd_locale_x11_model: pc105
