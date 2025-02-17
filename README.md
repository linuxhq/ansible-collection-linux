# linuxhq.linux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.linux-blue)](https://galaxy.ansible.com/linuxhq/linux)
[![Lint](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/pre-commit.yml)
[![Release](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml)

A collection of linux roles

# Collection

## Build

    ansible-galaxy collection build

## Install

    ansible-galaxy collection install linuxhq.linux

## Molecule

    /usr/bin/python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt

# Playbook

An example playbook utilizing roles available in this collection

    - hosts: server
      roles:
        - role: linuxhq.linux.group
          group_list:
            - name: linuxhq
              gid: 2000

        - role: linuxhq.linux.user
          user_list:
            - name: linuxhq
              uid: 2000

