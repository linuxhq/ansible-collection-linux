# systemd\_networkd

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A system daemon that manages network configurations

## Requirements

None

## Role Variables

    systemd_networkd_conf: {}
    systemd_networkd_files: []

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.systemd_networkd
          systemd_networkd_conf:
            network:
              ManageForeignRoutes: true
              ManageForeignRoutingPolicyRules: true
              RouteTable:
              SpeedMeter: false
              SpeedMeterIntervalSec: 10s
            dhcpv4:
              DUIDRawData:
              DUIDType: vendor
            dhcpv6:
              DUIDRawData:
              DUIDType: vendor

          systemd_networkd_files:
            - name: "{{ ansible_facts.default_ipv4.interface }}"
              priority: 80
              match:
                Name: "{{ ansible_facts.default_ipv4.interface }}"
              network:
                DHCP: true
