# rpmfusion

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Merger of Dribble, Freshrpms, and Livna

## Requirements

* [Extra Packages for Enterprise Linux](https://docs.fedoraproject.org/en-US/epel/)

## Role Variables

    rpmfusion_packages: []
    rpmfusion_repositories:
      - name: rpmfusion-free-updates
        state: enabled
      - name: rpmfusion-nonfree-updates
        state: enabled

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.rpmfusion
          rpmfusion_packages:
            - kmod-VirtualBox
          rpmfusion_repositories:
            - name: rpmfusion-free-updates
              state: enabled
            - name: rpmfusion-free-updates-source
              state: enabled
            - name: rpmfusion-nonfree-updates
              state: enabled
            - name: rpmfusion-nonfree-updates-source
              state: enabled
