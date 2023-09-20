# openssh\_client

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

OpenSSH SSH client

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    openssh_client: []
    openssh_client_d: []
    openssh_client_include: /etc/ssh/ssh_config.d/*.conf

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.openssh_client
          openssh_client:
            AddressFamily: inet
            Ciphers: aes128-ctr,aes192-ctr,aes256-ctr
            ForwardAgent: no
            ForwardX11: no
            HashKnownHosts: yes
            LogLevel: ERROR
            MACs: hmac-sha2-256,hmac-sha2-512
            StrictHostKeyChecking: no
            UserKnownHostsFile: /dev/null
          openssh_client_d:
            - file: 01-linuxhq
              host: linuxhq.net
              options:
                HashKnownHosts: no
                LogLevel: QUIET
            - file: 02-tkimball
              host: taylorkimball.com
              options:
                ForwardAgent: yes
                ForwardX11: yes

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
