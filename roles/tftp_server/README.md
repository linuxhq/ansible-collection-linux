# tftp\_server

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Trivial File Transfer Protocol

## Requirements

None

## Role Variables

    tftp_server_exec_start: null
    tftp_server_packages:
      - tftp
      - tftp-server

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.tftp_server
          tftp_server_exec_start: /usr/sbin/in.tftpd -c -p -s /var/lib/tftpboot
