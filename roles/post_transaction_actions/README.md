# post\_transaction\_actions

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF post-transaction-actions Plugin

## Requirements

None

## Role Variables

    post_transaction_actions_dir: /etc/dnf/plugins/post-transaction-actions.d/
    post_transaction_actions_enabled: true
    post_transaction_actions_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.post_transaction_actions
          post_transaction_actions_list:
            - package_filter: kernel
              transaction_state: in
              command: /usr/sbin/grub2-set-default 0

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
