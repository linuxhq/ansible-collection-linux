# systemd\_localectl

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Control the system locale and keyboard layout settings

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    systemd_localectl_keymap: null
    systemd_localectl_locale: LANG=C.UTF-8
    systemd_localectl_x11_keymap: null

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_localectl
          systemd_localectl_keymap: us
          systemd_localectl_x11_keymap: us

## License

Copyright (C) 2025 Linux HeadQuarters

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
