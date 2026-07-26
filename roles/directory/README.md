# directory

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of directories on a host

## Requirements

None

## Role Variables

    directory_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.directory
          directory_list:
            - group: root
              mode: '0700'
              owner: root
              paths:
                - /dev/shm/root
            - group: vagrant
              mode: '0644'
              owner: vagrant
              paths:
                - /dev/shm/vagrant
