# openssh\_server

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

OpenSSH SSH daemon

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    openssh_server:
      - key: AcceptEnv
        value: LANG LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES
      - key: AcceptEnv
        value: LC_IDENTIFICATION LC_ALL LANGUAGE
      - key: AcceptEnv
        value: LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT
      - key: AcceptEnv
        value: XMODIFIERS
      - key: AuthorizedKeysFile
        value: .ssh/authorized_keys
      - key: ChallengeResponseAuthentication
        value: 'no'
      - key: GSSAPIAuthentication
        value: 'yes'
      - key: GSSAPICleanupCredentials
        value: 'no'
      - key: HostKey
        value: /etc/ssh/ssh_host_ecdsa_key
      - key: HostKey
        value: /etc/ssh/ssh_host_ed25519_key
      - key: HostKey
        value: /etc/ssh/ssh_host_rsa_key
      - key: PasswordAuthentication
        value: 'no'
      - key: PermitRootLogin
        value: 'yes'
      - key: PrintMotd
        value: 'no'
      - key: Subsystem
        value: sftp /usr/libexec/openssh/sftp-server
      - key: SyslogFacility
        value: AUTHPRIV
      - key: UsePAM
        value: 'yes'
      - key: X11Forwarding
        value: 'yes'
    openssh_server_autocreate_server_keys: []
    openssh_server_crypto_policy: null
    openssh_server_use_strong_rng: false

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.openssh_server
          openssh_server:
            - key: AddressFamily
              value: inet
            - key: AllowAgentForwarding
              value: 'no'
            - key: ChallengeResponseAuthentication
              value: 'no'
            - key: Ciphers
              value: aes128-ctr,aes192-ctr,aes256-ctr
            - key: ClientAliveCountMax
              value: '0'
            - key: ClientAliveInterval
              value: '300'
            - key: Compression
              value: delayed
            - key: GSSAPIAuthentication
              value: 'no'
            - key: GSSAPICleanupCredentials
              value: 'yes'
            - key: HostbasedAuthentication
              value: 'no'
            - key: HostKey
              value: /etc/ssh/ssh_host_rsa_key
            - key: HostKey
              value: /etc/ssh/ssh_host_ecdsa_key
            - key: HostKey
              value: /etc/ssh/ssh_host_ed25519_key
            - key: IgnoreRhosts
              value: 'yes'
            - key: KerberosAuthentication
              value: 'no'
            - key: LogLevel
              value: INFO
            - key: LoginGraceTime
              value: '30'
            - key: MACs
              value: hmac-sha2-256,hmac-sha2-512
            - key: PasswordAuthentication
              value: 'no'
            - key: PermitEmptyPasswords
              value: 'no'
            - key: PermitRootLogin
              value: 'no'
            - key: PermitUserEnvironment
              value: 'no'
            - key: PrintLastLog
              value: 'yes'
            - key: PrintMotd
              value: 'yes'
            - key: Port
              value: '22'
            - key: Protocol
              value: '2'
            - key: PubkeyAuthentication
              value: 'yes'
            - key: StrictModes
              value: 'yes'
            - key: Subsystem
              value: sftp internal-sftp -p close,lstat,mkdir,open,realpath,write
            - key: SyslogFacility
              value: AUTHPRIV
            - key: TCPKeepAlive
              value: 'yes'
            - key: UseDNS
              value: 'no'
            - key: UsePAM
              value: 'yes'
            - key: X11Forwarding
              value: 'no'

## License

Copyright (C) 2023 Linux HeadQuarters

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
