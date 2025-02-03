# openssh\_server

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

OpenSSH SSH daemon

## Requirements

None

## Role Variables

    openssh_server_parameters:
      AcceptEnv:
        - LANG LC_CTYPE LC_NUMERIC LC_TIME LC_COLLATE LC_MONETARY LC_MESSAGES
        - LC_IDENTIFICATION LC_ALL LANGUAGE
        - LC_PAPER LC_NAME LC_ADDRESS LC_TELEPHONE LC_MEASUREMENT
        - XMODIFIERS
      AuthorizedKeysFile: .ssh/authorized_keys
      ChallengeResponseAuthentication: false
      GSSAPIAuthentication: true
      GSSAPICleanupCredentials: false
      HostKey:
        - /etc/ssh/ssh_host_ecdsa_key
        - /etc/ssh/ssh_host_ed25519_key
        - /etc/ssh/ssh_host_rsa_key
      PasswordAuthentication: false
      PermitRootLogin: true
      PrintMotd: false
      Subsystem: sftp /usr/libexec/openssh/sftp-server
      SyslogFacility: AUTHPRIV
      UsePAM: true
      X11Forwarding: true

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.openssh_server
          openssh_server_parameters:
            AddressFamily: inet
            AllowAgentForwarding: false
            ChallengeResponseAuthentication: false
            Ciphers: aes128-ctr,aes192-ctr,aes256-ctr
            ClientAliveCountMax: 0
            ClientAliveInterval: 300
            Compression: delayed
            GSSAPIAuthentication: false
            GSSAPICleanupCredentials: true
            HostbasedAuthentication: false
            HostKey:
              - /etc/ssh/ssh_host_rsa_key
              - /etc/ssh/ssh_host_ecdsa_key
              - /etc/ssh/ssh_host_ed25519_key
            IgnoreRhosts: true
            KerberosAuthentication: false
            LogLevel: INFO
            LoginGraceTime: 30
            MACs: hmac-sha2-256,hmac-sha2-512
            PasswordAuthentication: false
            PermitEmptyPasswords: false
            PermitRootLogin: false
            PermitUserEnvironment: false
            PrintLastLog: true
            PrintMotd: true
            Port: 22
            Protocol: 2
            PubkeyAuthentication: true
            StrictModes: true
            Subsystem: sftp internal-sftp -p close,lstat,mkdir,open,realpath,write
            SyslogFacility: AUTHPRIV
            TCPKeepAlive: true
            UseDNS: false
            UsePAM: true
            X11Forwarding: false

## License

Copyright (C) 2025 Linux HeadQuarters

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
