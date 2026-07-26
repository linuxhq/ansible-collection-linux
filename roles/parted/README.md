# parted

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Configure block device partitions

## Requirements

None

## Role Variables

    parted_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.parted
          parted_list:
            - device: /dev/sdb
              label: gpt
              partitions:
                - number: 1
                  part_end: '100%'
                  part_start: '0%'
                  part_type: primary
