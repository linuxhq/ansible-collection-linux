# setup

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Configure setup package contents

## Requirements

None

## Role Variables

    setup_aliases: []
    setup_environment: []
    setup_hosts: []
    setup_hostname: null
    setup_motd: null
    setup_profile_d: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.setup
          setup_aliases:
            - key: postmaster
              value: root
          setup_environment:
            - key: linuxhq
              value: development
          setup_hostname: linuxhq.net
          setup_hosts:
            - ip: 1.1.1.1
              hosts:
                - linuxhq.net
                - linuxhq.org
          setup_motd: |
            QWxsIHlvdXIgYmFzZSBhcmUgYmVsb25nIHRvIHVzCg==
          setup_profile_d:
            - name: linuxhq.sh
              script: |
                ZXhwb3J0IFRNT1VUPTMwMAo=

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
