# package

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Manage presence of packages on a host

## Requirements

None

## Role Variables

    package_apt_allow_change_held_packages: false
    package_apt_allow_downgrade: false
    package_apt_allow_unauthenticated: false
    package_apt_autoclean: false
    package_apt_autoremove: false
    package_apt_clean: false
    package_apt_dpkg_options:
      - force-confdef
      - force-confold
    package_apt_fail_on_autoremove: false
    package_apt_force: false
    package_apt_force_apt_get: false
    package_apt_lock_timeout: 60
    package_apt_only_upgrade: false
    package_apt_purge: false
    package_apt_update_cache: false
    package_apt_update_cache_retries: 5
    package_apt_update_cache_retry_max_delay: 12
    package_dnf_allow_downgrade: false
    package_dnf_allowerasing: false
    package_dnf_autoremove: false
    package_dnf_cacheonly: false
    package_dnf_disable_gpg_check: false
    package_dnf_disable_plugin: []
    package_dnf_disablerepo: []
    package_dnf_enable_plugin: []
    package_dnf_enablerepo: []
    package_dnf_exclude: []
    package_dnf_install_weak_deps: true
    package_dnf_installroot: /
    package_dnf_lock_timeout: 30
    package_dnf_skip_broken: false
    package_dnf_sslverify: true
    package_dnf_update_cache: false
    package_dnf_use_backend: auto
    package_dnf_validate_certs: true
    package_list: []

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.package
          package_list:
            - name: httpd
            - name: tuned
              state: absent

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
