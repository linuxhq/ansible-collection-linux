# nscd

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Name service cache daemon

## Requirements

None

## Role Variables

    nscd_debug_level: 0
    nscd_logfile: /var/log/nscd.log
    nscd_max_threads: 32
    nscd_paranoia: false
    nscd_reload_count: 5
    nscd_restart_interval: 3600
    nscd_server_user: nscd
    nscd_stat_user: nscd
    nscd_threads: 4
    nscd_group_auto_propagate: true
    nscd_group_check_files: true
    nscd_group_enable_cache: true
    nscd_group_max_db_size: 33554432
    nscd_group_negative_time_to_live: 60
    nscd_group_persistent: true
    nscd_group_positive_time_to_live: 3600
    nscd_group_shared: true
    nscd_group_suggested_size: 211
    nscd_hosts_check_files: true
    nscd_hosts_enable_cache: true
    nscd_hosts_max_db_size: 33554432
    nscd_hosts_negative_time_to_live: 20
    nscd_hosts_persistent: true
    nscd_hosts_positive_time_to_live: 3600
    nscd_hosts_shared: true
    nscd_hosts_suggested_size: 211
    nscd_netgroup_check_files: true
    nscd_netgroup_enable_cache: true
    nscd_netgroup_max_db_size: 33554432
    nscd_netgroup_negative_time_to_live: 20
    nscd_netgroup_persistent: true
    nscd_netgroup_positive_time_to_live: 28800
    nscd_netgroup_shared: true
    nscd_netgroup_suggested_size: 211
    nscd_passwd_auto_propagate: true
    nscd_passwd_check_files: true
    nscd_passwd_enable_cache: true
    nscd_passwd_max_db_size: 33554432
    nscd_passwd_negative_time_to_live: 20
    nscd_passwd_persistent: true
    nscd_passwd_positive_time_to_live: 600
    nscd_passwd_shared: true
    nscd_passwd_suggested_size: 211
    nscd_services_check_files: true
    nscd_services_enable_cache: true
    nscd_services_max_db_size: 33554432
    nscd_services_negative_time_to_live: 20
    nscd_services_persistent: true
    nscd_services_positive_time_to_live: 28800
    nscd_services_shared: true
    nscd_services_suggested_size: 211

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.nscd
          nscd_debug_level: 1

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
