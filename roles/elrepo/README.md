# elrepo

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

ELRepo Project

## Requirements

None

## Role Variables

    elrepo_kernel: false
    elrepo_kernel_version: lt
    elrepo_packages: []
    elrepo_repositories:
      - name: elrepo
        state: enabled

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.elrepo
          elrepo_kernel: true
          elrepo_kernel_version: ml
          elrepo_packages:
            - kmod-a3818
