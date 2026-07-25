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
