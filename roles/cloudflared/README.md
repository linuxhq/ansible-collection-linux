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
    cloudflared_tunnels: []
    cloudflared_user: root

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.cloudflared
          cloudflared_tunnels:
            - name: linuxhq.net
              token: >
                eyJhIjoiMzFhMTQ2NDRmZmI0NjJlODg3NDEyYWVhZDRjNWM0NmUiLCJ0IjoiMTBjNDE5YzUtZWU1NS00ZTA1LTk0MDUtYzMzYjY4NDgwNmY1IiwicyI6IldyeGFBb1Vzc014OXVQM3hYSHF0b2tKYlZSeWloWGJIM3VLRW9WYm9KcGVFVld2Zkt2d2JMaFRUS3BSZWNSckVrNGZwWGthRUh5Zm5lOUxWZWJNVG00PT0ifQ==

            - name: linuxhq.org
              token: >
                eyJhIjoiNGZjY2ZiZGY0Y2VmYTM5MjE2ZTM1NGM4NTgxN2U0YTciLCJ0IjoiZDVhNzI4Y2QtODg0Mi00ZDE5LWI3OGEtYjE0ZDMwYjljMmVhIiwicyI6ImVBS29IS3pOTG1pZXdtdEV2YXRYb0Vjc3VGS3M3OWt6ajRQTEtITWpGTXV5VVBQclBOSmdKc1BGcWg5VGlwaXJhaUtueUxNdlB6b2d1bUprcEFhYWNhPT0ifQ==

## License

Copyright (c) Linux HeadQuarters

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
