# msmtpd

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A minimal SMTP server

## Requirements

* [podman](https://podman.io)

## Role Variables

    msmtpd_auth: false
    msmtpd_from: null
    msmtpd_gidmap: '0:2147483647:65536'
    msmtpd_host: null
    msmtpd_image: docker.io/crazymax/msmtpd:latest
    msmtpd_no_log: false
    msmtpd_password: null
    msmtpd_port: 587
    msmtpd_publish: 127.0.0.1:25:2500
    msmtpd_starttls: true
    msmtpd_tls: false
    msmtpd_uidmap: '0:2147483647:65536'
    msmtpd_user: null

## Dependencies

* [podman](../podman)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.msmtpd
          msmtpd_from: molecule@example.com
          msmtpd_host: smtp.example.com
          msmtpd_password: molecule
          msmtpd_user: molecule@example.com
