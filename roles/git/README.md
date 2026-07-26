# git

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Clone git repositories

## Requirements

None

## Role Variables

    git_packages:
      - git
    git_repositories: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.git
          git_repositories:
            - repo: https://github.com/linuxhq/ansible-collection-aws.git
              dest: /usr/local/ansible-collection-aws
              become: true

            - repo: https://github.com/linuxhq/ansible-collection-linux.git
              dest: /home/vagrant/ansible-collection-linux
