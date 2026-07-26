# setup

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Configure setup package contents

## Requirements

None

## Role Variables

    setup_aliases: []
    setup_environment: []
    setup_hosts: []
    setup_hostname: null
    setup_motd: null
    setup_profile_d: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.setup
          setup_aliases:
            - key: postmaster
              value: root
          setup_environment:
            - key: linuxhq
              value: development
          setup_hostname: linuxhq.net
          setup_hosts:
            - ip: 1.1.1.1
              hosts:
                - linuxhq.net
                - linuxhq.org
          setup_motd: |
            QWxsIHlvdXIgYmFzZSBhcmUgYmVsb25nIHRvIHVzCg==
          setup_profile_d:
            - name: linuxhq.sh
              script: |
                ZXhwb3J0IFRNT1VUPTMwMAo=
