# rssh

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Restricted shell for scp/sftp

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    rssh_allow: []
    rssh_chrootpath: null
    rssh_group: rsshusers
    rssh_logfacility: LOG_USER
    rssh_shell: /usr/bin/rssh
    rssh_umask: '022'
    rssh_users: []

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.rssh
          rssh_allow:
            - rsync
            - sftp
          rssh_users:
            - name: linuxhq
              access_bits: '10000'
              umask: '077'

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
