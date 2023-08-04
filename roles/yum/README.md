# yum

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Yellowdog Updater Modified

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    yum_absent: []
    yum_cachedir: /var/cache/yum/$basearch/$releasever
    yum_debuglevel: 2
    yum_disablerepo: []
    yum_distroverpkg: centos-release
    yum_enablerepo: []
    yum_exactarch: true
    yum_gpgcheck: true
    yum_installonly_limit: 5
    yum_keepcache: false
    yum_logfile: /var/log/yum.log
    yum_obsoletes: true
    yum_override_install_langs: en_US.UTF-8
    yum_plugins: true
    yum_present: []
    yum_tsflags: nodocs
    yum_update: false
    yum_update_cache: false

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.yum
          yum_present:
            - python-virtualenv
          yum_update: true

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
