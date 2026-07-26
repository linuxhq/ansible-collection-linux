# epel

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Extra Packages for Enterprise Linux

## Requirements

None

## Role Variables

    epel_packages: []
    epel_repositories:
      - name: epel
        state: enabled

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.epel
          epel_packages:
            - msmtp
          epel_repositories:
            - name: epel
              state: enabled
            - name: epel-debuginfo
              state: disabled
            - name: epel-testing
              state: enabled
