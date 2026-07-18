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

## Requirements

* Python `>= 3.13`
* `ansible-core >= 2.18.0`
* `ansible.posix`
* `community.docker >= 5.0.0`
* `community.general >= 12.0.0`
* `pycryptodome >= 3.23.0` (rclone filter plugins only)

## Molecule

    make
    source venv/bin/activate

# Playbook

An example playbook utilizing roles available in this collection

    - hosts: server
      vars:
        global_users:
          - name: johnd
            id: 2000
            key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIRtpHq0ih6ZsXzskVMqHLc3bvCp82l1lS/V9i3wXwQQ
          - name: janed
            id: 2001
            key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEQYZwthruEeeRtn4QE2x5xeVosMNha99UOVptoNjVbs

      roles:
        - role: linuxhq.linux.group
          group_list:
            "{{ (global_users |
                json_query('[].{
                  name: name,
                  gid: id
                }')) |
                d([]) }}"

        - role: linuxhq.linux.user
          user_list:
            "{{ (global_users |
                json_query('[].{
                  name: name,
                  uid: id
                }')) |
                d([]) }}"

        - role: linuxhq.linux.authorized_key
          authorized_key_list:
            "{{ (global_users |
                json_query('[].{
                  user: name,
                  key: key,
                  exclusive: `true`
                }')) |
                d([]) }}"
