# postfix

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A free and open-source mail transfer agent

## Requirements

None

## Role Variables

    postfix_lookup_tables: []
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

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.postfix
          postfix_lookup_tables:
            - name: sender_canonical
              database: regexp
              postmap: false
              content: |
                /^(.*)@(.*)\.localdomain$/ ${1}@${2}.linuxhq.net

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
            newaliases_path: /usr/bin/newaliases.postfix
            relayhost: mta.linuxhq.net:587
            sendmail_path: /usr/sbin/sendmail.postfix
            sender_canonical_maps: regexp:/etc/postfix/sender_canonical
            setgid_group: postdrop
            smtp_sasl_security_options: noanonymous
            queue_directory: /var/spool/postfix
            unknown_local_recipient_reject_code: 550

          postfix_service_submission: true

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
