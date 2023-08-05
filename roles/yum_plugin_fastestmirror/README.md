# yum\_plugin\_fastestmirror

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

YUM Plugin - Fastest Mirror

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    yum_plugin_fastestmirror_always_print_best_host: true
    yum_plugin_fastestmirror_enabled: true
    yum_plugin_fastestmirror_exclude: []
    yum_plugin_fastestmirror_hostfilepath: timedhosts.txt
    yum_plugin_fastestmirror_include_only: []
    yum_plugin_fastestmirror_maxhostfileage: 10
    yum_plugin_fastestmirror_maxthreads: 15
    yum_plugin_fastestmirror_prefer: null
    yum_plugin_fastestmirror_socket_timeout: 3
    yum_plugin_fastestmirror_verbose: false

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.yum_plugin_fastestmirror
          yum_plugin_fastestmirror_exclude:
            - .gov
            - facebook
          yum_plugin_fastestmirror_include_only:
            - .nl
            - .de
            - .uk
            - .ie
          yum_plugin_fastestmirror_verbose: true

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
