# cloudflared

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage cloudflared tunnels

## Requirements

None

## Role Variables

    cloudflared_command: tunnel run
    cloudflared_dir: /etc/cloudflared
    cloudflared_group: root
    cloudflared_packages:
      - cloudflared
    cloudflared_repository_stable: true
    cloudflared_rpm_key: https://pkg.cloudflare.com/cloudflare-ascii-pubkey.gpg
    cloudflared_tunnels: []
    cloudflared_user: root

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.cloudflared
          cloudflared_command: tunnel run -p http2
          cloudflared_tunnels:
            - name: linuxhq.net
              account_tag: 68b329da9893e34099c7d8ad5cb9c940
              id: ac5a6018-3af1-11ee-be56-0242ac120002
              ingress:
                - hostname: linuxhq.net
                  service: ssh://localhost:22
                - service: http_status:404
              secret: bUZVQVZ0UnNBcWtUUGV4M0N2WHpMUHpleVdxZ3RWZlQ3VldqeHFoN0plUHdqTkpGSnR0N1hxZm5IM0E3RXZDeg==

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
