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
