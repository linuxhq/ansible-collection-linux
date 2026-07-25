# tcp\_bbr

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

TCP Bottleneck Bandwidth and RRT

## Requirements

* kernel >= 4.9

## Role Variables

    tcp_bbr_modules:
      - sch_fq
      - tcp_bbr
    tcp_bbr_sysctl:
      - key: net.core.default_qdisc
        value: fq
      - key: net.ipv4.tcp_congestion_control
        value: bbr
    tcp_bbr_sysctl_file: /etc/sysctl.d/10-tcp_bbr.conf

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.tcp_bbr
