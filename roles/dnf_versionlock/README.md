# dnf\_versionlock

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

DNF versionlock Plugin

## Requirements

None

## Role Variables

    dnf_versionlock_enabled: true
    dnf_versionlock_locklist: /etc/dnf/plugins/versionlock.list
    dnf_versionlock_packages: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.dnf_versionlock
          dnf_versionlock_packages:
            - name: docker-ce
              version: '3:25.0.5-1.el9.*'
            - name: docker-ce-cli
              version: '1:25.0.5-1.el9.*'
            - name: docker-ce-rootless-extras
              version: '0:25.0.5-1.el9.*'
            - name: containerd.io
              version: '0:1.6.28-3.2.el9.*'
