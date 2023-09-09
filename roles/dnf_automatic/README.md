# dnf\_automatic

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF Automatic

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    dnf_automatic_base_debuglevel: 1
    dnf_automatic_command_command_format: cat
    dnf_automatic_command_stdin_format: '{body}'
    dnf_automatic_command_email_command_format: >-
      mail -Ssendwait -s {subject} -r {email_from} {email_to}
    dnf_automatic_command_email_email_from: root
    dnf_automatic_command_email_email_to: root
    dnf_automatic_command_email_stdin_format: '{body}'
    dnf_automatic_commands_apply_updates: false
    dnf_automatic_commands_download_updates: true
    dnf_automatic_commands_network_online_timeout: 60
    dnf_automatic_commands_random_sleep: 0
    dnf_automatic_commands_reboot: never
    dnf_automatic_commands_reboot_command: >-
      shutdown -r +5 'Rebooting after applying package updates'
    dnf_automatic_commands_upgrade_type: default
    dnf_automatic_email_email_from: root
    dnf_automatic_email_email_host: localhost
    dnf_automatic_email_email_port: 25
    dnf_automatic_email_email_to: root
    dnf_automatic_emitters_emit_via: stdio
    dnf_automatic_emitters_system_name: "{{ inventory_hostname }}"
    dnf_automatic_timer: dnf-automatic-notifyonly.timer

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.dnf_automatic
          dnf_automatic_commands_apply_updates: true
          dnf_automatic_timer: dnf-automatic-install.timer

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
