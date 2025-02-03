# unbound

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A validating, recursive, caching DNS resolver

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

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
