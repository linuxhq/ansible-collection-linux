# lux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Lux YUM repository

## Requirements

None

## Role Variables

    lux_packages: []
    lux_repositories:
      - name: frank
        state: enabled
      - name: lux
        state: enabled

## Dependencies

* [epel](../epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.lux
          lux_packages:
            - ppp
