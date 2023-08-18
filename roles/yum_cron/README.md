# yum\_cron

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

An interface to conveniently call yum from cron

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    yum_cron_apply_updates: false
    yum_cron_assumeyes: false
    yum_cron_debuglevel: -2
    yum_cron_download_updates: true
    yum_cron_email_from: root@localhost
    yum_cron_email_host: localhost
    yum_cron_email_to: root
    yum_cron_emit_via: stdio
    yum_cron_group_list: []
    yum_cron_group_package_types:
      - mandatory
      - default
    yum_cron_hourly_apply_updates: false
    yum_cron_hourly_assumeyes: false
    yum_cron_hourly_debuglevel: -2
    yum_cron_hourly_download_updates: false
    yum_cron_hourly_email_from: root@localhost
    yum_cron_hourly_email_host: localhost
    yum_cron_hourly_email_to: root
    yum_cron_hourly_emit_via: stdio
    yum_cron_hourly_group_list: []
    yum_cron_hourly_group_package_types:
      - mandatory
      - default
    yum_cron_hourly_mdpolicy: 'group:main'
    yum_cron_hourly_output_width: 80
    yum_cron_hourly_random_sleep: 15
    yum_cron_hourly_system_name: "{{ inventory_hostname }}"
    yum_cron_hourly_update_cmd: default
    yum_cron_hourly_update_messages: false
    yum_cron_mdpolicy: 'group:main'
    yum_cron_output_width: 80
    yum_cron_random_sleep: 120
    yum_cron_system_name: "{{ inventory_hostname }}"
    yum_cron_update_cmd: default
    yum_cron_update_messages: true

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.yum_cron
          yum_cron_apply_updates: true
          yum_cron_hourly_apply_updates: true

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
