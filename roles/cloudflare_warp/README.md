# cloudflare\_warp

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage cloudflare warp tunnels

## Requirements

None

## Role Variables

    cloudflare_warp_no_color: false
    cloudflare_warp_log_level_max: info
    cloudflare_warp_scripts: []
    cloudflare_warp_token: null

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.cloudflare_warp
          cloudflare_warp_no_color: true
          cloudflare_warp_log_level_max: warning
          cloudflare_warp_token: "{{ lookup('env', 'CLOUDFLARE_WARP_TOKEN') }}"
