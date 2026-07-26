# template

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of templates on a host

## Requirements

None

## Role Variables

    template_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.template
          template_list:
            - dest: /etc/aliases
              src: /path/to/aliases.j2
            - dest: /etc/environment
              src: /path/to/environment.j2
