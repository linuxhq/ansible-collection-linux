# pam\_ssh\_agent\_auth

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

PAM module for granting permissions based on SSH agent requests

## Requirements

None

## Role Variables

    pam_ssh_agent_auth_file: /etc/security/authorized_keys
    pam_ssh_agent_auth_keys: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.pam_ssh_agent_auth
          pam_ssh_agent_auth_keys:
            - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDFgaw1OtDFwiaY+lccD1UvXzEU5bNTdGQhOoyYyGcwo

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
