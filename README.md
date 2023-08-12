# linuxhq.linux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.linux-blue)](https://galaxy.ansible.com/linuxhq/linux)
[![Lint](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/linting.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/linting.yml)
[![Release](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml)

A collection of linux roles

# Collection

## Build

    ansible-galaxy collection build

## Install

    ansible-galaxy collection install linuxhq.linux

## Molecule

    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt

# Playbook

An example playbook utilizing roles available in this collection

    - hosts: server
      collections:
        - linuxhq.linux
      vars:
        groupadd:
          - name: linuxhq
            gid: 2000
        useradd:
          - name: tkimball
            group: linuxhq
            uid: 2001
      roles:
        - linuxhq.linux.group
        - linuxhq.linux.user
