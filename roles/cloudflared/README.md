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
