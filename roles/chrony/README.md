# chrony

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Programs for keeping computer clocks accurate

## Requirements

None

## Role Variables

    chrony_conf:
      - driftfile /var/lib/chrony/drift
      - keyfile /etc/chrony.keys
      - leapsectz right/UTC
      - logdir /var/log/chrony
      - makestep 1.0 3
      - ntsdumpdir /var/lib/chrony
      - pool 1.pool.ntp.org iburst
      - pool 2.pool.ntp.org iburst
      - pool 3.pool.ntp.org iburst
      - rtcsync
      - sourcedir /run/chrony-dhcp
    chrony_options: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.chrony
          chrony_conf:
            - authselectmode require
            - cmdport 0
            - driftfile /var/lib/chrony/drift
            - hwtimestamp *
            - log measurements statistics tracking
            - logdir /var/log/chrony
            - makestep 1.0 3
            - minsources 2
            - ntsdumpdir /var/lib/chrony
            - rtcsync
            - server ntppool1.time.nl iburst nts
            - server ntppool2.time.nl iburst nts
            - sourcedir /run/chrony-dhcp
          chrony_options:
            - '-F 1'
