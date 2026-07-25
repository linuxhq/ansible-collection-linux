# user

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of users on a host

## Requirements

None

## Role Variables

    user_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.user
          user_list:
            - name: johndoe
              uid: 1001
            - name: janedoe
              uid: 1002
