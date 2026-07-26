# sysctl

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Configure kernel parameters at runtime

## Requirements

None

## Role Variables

    sysctl_conf: []
    sysctl_d: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.sysctl
          sysctl_conf:
            kernel.dmesg_restrict: 1
            kernel.modules_disabled: 1
          sysctl_d:
            - name: 98-ansible
              parameters:
                kernel.panic: 1
                vm.swappiness: 5
