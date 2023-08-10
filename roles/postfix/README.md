# postfix

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A free and open-source mail transfer agent

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    postfix_databases:
      - btree
      - cdb
      - dbm
      - hash
      - fail
      - sdbm
    postfix_packages:
      - postfix
    postfix_parameters:
      alias_database: hash:/etc/aliases
      alias_maps: hash:/etc/aliases
      command_directory: /usr/sbin
      daemon_directory: /usr/libexec/postfix
      data_directory: /var/lib/postfix
      debug_peer_level: 2
      html_directory: false
      inet_interfaces: localhost
      inet_protocols: all
      mail_owner: postfix
      mailq_path: /usr/bin/mailq.postfix
      manpage_directory: /usr/share/man
      mydestination:
        - $myhostname
        - localhost.$mydomain
        - localhost
      newaliases_path: /usr/bin/newaliases.postfix
      sendmail_path: /usr/sbin/sendmail.postfix
      setgid_group: postdrop
      queue_directory: /var/spool/postfix
      unknown_local_recipient_reject_code: 550
    postfix_generic_maps: []
    postfix_recipient_canonical_maps: []
    postfix_sender_canonical_maps: []

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.postfix
          postfix_generic_maps:
            - pattern: root
              address: noreply@linuxhq.org
          postfix_packages:
            - cyrus-sasl
            - cyrus-sasl-lib
            - cyrus-sasl-plain
            - postfix
          postfix_parameters:
            alias_database: hash:/etc/aliases
            alias_maps: hash:/etc/aliases
            command_directory: /usr/sbin
            daemon_directory: /usr/libexec/postfix
            data_directory: /var/lib/postfix
            inet_interfaces: localhost
            inet_protocols: all
            mail_owner: postfix
            mailq_path: /usr/bin/mailq.postfix
            manpage_directory: /usr/share/man
            myhostname: "{{ inventory_hostname }}"
            mydomain: "{{ inventory_hostname }}"
            mynetworks:
              - 192.168.0.0/24
            newaliases_path: /usr/bin/newaliases.postfix
            recipient_canonical_maps: regexp:/etc/postfix/recipient_canonical
            relayhost: '[mail.linuxhq.org]:587'
            sendmail_path: /usr/sbin/sendmail.postfix
            sender_canonical_maps: regexp:/etc/postfix/sender_canonical
            setgid_group: postdrop
            smtp_generic_maps: hash:/etc/postfix/generic
            smtp_sasl_auth_enable: true
            smtp_sasl_password_maps: hash:/etc/postfix/sasl_passwd
            smtp_sasl_security_options: noanonymous
            smtp_tls_CAfile: /etc/ssl/certs/ca-bundle.crt
            smtp_tls_security_level: encrypt
            smtp_use_tls: true
            queue_directory: /var/spool/postfix
            unknown_local_recipient_reject_code: 550
          postfix_sasl_password: mzh3SfKATIYP22qlRKIQnw51
          postfix_sasl_username: noreply@linuxhq.org
          postfix_recipient_canonical_maps:
            - pattern: /.+/
              address: noreply@linuxhq.org
          postfix_sender_canonical_maps:
            - pattern: /.+/
              address: noreply@linuxhq.org

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
