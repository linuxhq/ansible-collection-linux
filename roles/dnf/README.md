# dnf

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Dandified Yum

## Requirements

None

## Role Variables

    dnf_conf:
      main:
        best: true
        clean_requirements_on_remove: true
        gpgcheck: true
        installonly_limit: 3
        skip_if_unavailable: false
    dnf_protected_d:
      - name: dnf
        packages:
          - dnf

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.dnf
          dnf_conf:
            main:
              best: true
              clean_requirements_on_remove: true
              gpgcheck: true
              installonly_limit: 3
              log_compress: true
              logdir: /var/log
              skip_broken: false
              skip_if_unavailable: false
          dnf_protected_d:
            - name: shim
              packages:
                - shim-aa64
                - shim-arm
                - shim-ia32
                - shim-x64

## License

Copyright (c) Linux HeadQuarters

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
