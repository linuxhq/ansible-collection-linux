# openssh\_client

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

OpenSSH SSH client

## Requirements

None

## Role Variables

    openssh_client_include: /etc/ssh/ssh_config.d/*.conf
    openssh_client_parameters: {}
    openssh_client_parameters_d: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.openssh_client
          openssh_client_parameters:
            AddressFamily: inet
            Ciphers: aes128-ctr,aes192-ctr,aes256-ctr
            ForwardAgent: false
            ForwardX11: false
            HashKnownHosts: true
            LogLevel: ERROR
            MACs: hmac-sha2-256,hmac-sha2-512
            StrictHostKeyChecking: false
            UserKnownHostsFile: /dev/null
          openssh_client_parameters_d:
            - name: linuxhq-net.conf
              host: linuxhq.net
              parameters:
                HashKnownHosts: false
                LogLevel: QUIET
            - name: linuxhq-org.conf
              host: linuxhq.org
              parameters:
                ForwardAgent: true
                ForwardX11: true
