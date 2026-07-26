# remi

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Remi's RPM repository

## Requirements

None

## Role Variables

    remi_baseurl: 'https://rpms.remirepo.net'
    remi_packages: []
    remi_release: "remi-release-{{ ansible_facts.distribution_major_version }}.rpm"
    remi_repositories:
      - name: remi-modular
        state: enabled
      - name: remi-safe
        state: enabled

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.remi
          remi_packages:
            - @php:remi-8.5
