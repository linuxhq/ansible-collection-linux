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
