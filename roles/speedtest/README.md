# speedtest

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Official Ookla Speedtest CLI

## Requirements

None

## Role Variables

    speedtest_packages:
      - speedtest
    speedtest_repositories:
      - name: ookla_speedtest-cli
        state: enabled

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - linuxhq.linux.speedtest
