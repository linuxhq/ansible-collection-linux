# template

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of templates on a host

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    templates: []

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.template
          templates:
            - group: linuxhq
              mode: '0644'
              owner: linuxhq
              path_dest: /home/linuxhq/containers
              path_src: "{{ lookup('env', 'PWD') ~ '/templates' }}"
              paths:
                - dest: certbot/config/cloudflare.ini
                  src: certbot/cloudflare.ini.j2
                - dest: openssh-server/config/pubkeys/linuxhq
                  mode: '0600'
                  src: openssh-server/pubkey.j2

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
