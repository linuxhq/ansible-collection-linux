# unbound

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A validating, recursive, caching DNS resolver

## Requirements

None

## Role Variables

    unbound_auth_zones: {}
    unbound_cachedb: {}
    unbound_dnscrypt: {}
    unbound_dnstap: {}
    unbound_dynlib: {}
    unbound_forward_zones: {}
    unbound_include: /etc/unbound/conf.d/*.conf
    unbound_ipset: {}
    unbound_python: {}
    unbound_remote_control: {}
    unbound_rpzs: {}
    unbound_server: {}
    unbound_stub_zones: {}
    unbound_views: {}

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.unbound
          unbound_forward_zones:
            '.':
              forward-addr:
                - '1.1.1.1@853#cloudflare-dns.com'
                - '1.0.0.1@853#cloudflare-dns.com'
              forward-first: false
              forward-tls-upstream: true
          unbound_server:
            interface: 127.0.0.1
            tls-cert-bundle: /etc/pki/tls/certs/ca-bundle.crt
