# systemd\_resolved

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A systemd service that provides network name resolution to local applications

## Requirements

None

## Role Variables

    systemd_resolved_conf:
      DNS: '8.8.8.8 8.8.4.4'
    systemd_resolved_symlink: /run/systemd/resolve/stub-resolv.conf

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_resolved
          systemd_resolved_conf:
            Cache: true
            DNS: '8.8.8.8#dns.google 8.8.4.4#dns.google'
            DNSStubListenerExtra:
              - 172.17.0.1
              - 192.168.0.1
            FallbackDNS: '1.1.1.1#cloudflare-dns.com 1.0.0.1#cloudflare-dns.com'
            DNSOverTLS: true
            DNSSEC: true
            LLMNR: false
