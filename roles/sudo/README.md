# sudo

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Execute a command as another user

## Requirements

None

## Role Variables

    sudo_aliases: []
    sudo_d: []
    sudo_defaults:
      - key: always_set_home
        value: true
      - key: env_reset
        value: true
      - key: match_group_by_gid
        value: true
      - key: requiretty
        value: false
      - key: visiblepw
        value: false
    sudo_pam: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.sudo
          sudo_aliases:
            - type: cmnd
              aliases:
                - name: admin
                  list:
                    - /usr/sbin/passwd
                    - /usr/sbin/useradd
                    - /usr/sbin/userdel
                - name: shutdown
                  list:
                    - /sbin/halt
                    - /sbin/poweroff
                    - /sbin/reboot
            - type: host
              aliases:
                - name: network
                  list:
                    - 192.168.0.0/255.255.255.0
            - type: runas
              aliases:
                - name: admins
                  list:
                    - root
            - type: user
              aliases:
                - name: users
                  list:
                    - tom
                    - mary
          sudo_d:
            - file: vagrant
              user: vagrant
              host: ALL
              runas: ALL
              commands:
                - NOPASSWD:ALL
          sudo_defaults:
            - key: always_set_home
              value: true
            - key: env_reset
              value: true
            - key: match_group_by_gid
              value: true
            - key: requiretty
              value: false
            - key: visiblepw
              value: false
            - key: env_keep
              value:
                - SSH_AUTH_SOCK
              operator: '+='
          sudo_pam:
            - module_interface: auth
              control_flag: sufficient
              module_name: pam_ssh_agent_auth.so
              module_arguments: file=/etc/security/authorized_keys
            - module_interface: auth
              control_flag: include
              module_name: system-auth
            - module_interface: account
              control_flag: include
              module_name: system-auth
            - module_interface: password
              control_flag: include
              module_name: system-auth
            - module_interface: session
              control_flag: include
              module_name: system-auth
