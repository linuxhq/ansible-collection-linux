# snoopy

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Snoopy Command Logger

## Requirements

None

## Role Variables

    snoopy_datasource_message_max_length: 2047
    snoopy_error_logging: false
    snoopy_filter_chain: []
    snoopy_log_message_max_length: 16383
    snoopy_message_format:
      - uid=%{uid}
      - tty=%{tty}
      - cmdline=%{cmdline}
    snoopy_output: devlog
    snoopy_packages:
      - snoopy
    snoopy_releasever: "{{ ansible_distribution_major_version }}"
    snoopy_repository_stable: true
    snoopy_rpm_key: https://a2o.github.io/snoopy-packages/snoopy-packages-key.pub
    snoopy_syslog_facility: LOG_AUTHPRIV
    snoopy_syslog_ident: snoopy
    snoopy_syslog_level: LOG_INFO

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.snoopy
          snoopy_filter_chain:
            - exclude_uid:0
          snoopy_message_format:
            - uid=%{uid}
            - sid=%{sid}
            - tty=%{tty}
            - cwd=%{cwd}
            - cmdline=%{cmdline}

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
