# transmission\_daemon

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

A fast, easy, and free bittorrent client

## Requirements

* [Extra Packages for Enterprise Linux](https://docs.fedoraproject.org/en-US/epel/)

## Role Variables

    transmission_daemon_alt_speed_down: 50
    transmission_daemon_alt_speed_enabled: false
    transmission_daemon_alt_speed_time_begin: 540
    transmission_daemon_alt_speed_time_day: 127
    transmission_daemon_alt_speed_time_enabled: false
    transmission_daemon_alt_speed_time_end: 1020
    transmission_daemon_alt_speed_up: 50
    transmission_daemon_bind_address_ipv4: '0.0.0.0'
    transmission_daemon_bind_address_ipv6: '::'
    transmission_daemon_blocklist_enabled: false
    transmission_daemon_blocklist_url: 'http://www.example.com/blocklist'
    transmission_daemon_cache_size_mb: 4
    transmission_daemon_dht_enabled: true
    transmission_daemon_download_dir: "{{ transmission_daemon_home }}/downloads"
    transmission_daemon_download_limit: 100
    transmission_daemon_download_limit_enabled: false
    transmission_daemon_download_queue_enabled: true
    transmission_daemon_download_queue_size: 5
    transmission_daemon_encryption: 1
    transmission_daemon_idle_seeding_limit: 30
    transmission_daemon_idle_seeding_limit_enabled: false
    transmission_daemon_incomplete_dir: "{{ transmission_daemon_home }}/downloads"
    transmission_daemon_incomplete_dir_enabled: false
    transmission_daemon_lpd_enabled: false
    transmission_daemon_max_peers_global: 200
    transmission_daemon_message_level: 1
    transmission_daemon_peer_congestion_algorithm: ''
    transmission_daemon_peer_id_ttl_hours: 6
    transmission_daemon_peer_limit_global: 200
    transmission_daemon_peer_limit_per_torrent: 50
    transmission_daemon_peer_port: 51413
    transmission_daemon_peer_port_random_high: 65535
    transmission_daemon_peer_port_random_low: 49152
    transmission_daemon_peer_port_random_on_start: false
    transmission_daemon_peer_socket_tos: 'default'
    transmission_daemon_pex_enabled: true
    transmission_daemon_port_forwarding_enabled: false
    transmission_daemon_preallocation: 1
    transmission_daemon_prefetch_enabled: true
    transmission_daemon_queue_stalled_enabled: true
    transmission_daemon_queue_stalled_minutes: 30
    transmission_daemon_ratio_limit: 2
    transmission_daemon_ratio_limit_enabled: false
    transmission_daemon_rename_partial_files: true
    transmission_daemon_rpc_authentication_required: true
    transmission_daemon_rpc_bind_address: 0.0.0.0
    transmission_daemon_rpc_enabled: true
    transmission_daemon_rpc_host_whitelist: []
    transmission_daemon_rpc_host_whitelist_enabled: true
    transmission_daemon_rpc_password: '{bd7f63c765c86ded1008510ec2b6988279f37a8cQpoGL86X'
    transmission_daemon_rpc_port: 9091
    transmission_daemon_rpc_url: '/transmission/'
    transmission_daemon_rpc_username: transmission
    transmission_daemon_rpc_whitelist:
      - 127.0.0.1
    transmission_daemon_rpc_whitelist_enabled: true
    transmission_daemon_scrape_paused_torrents_enabled: true
    transmission_daemon_script_torrent_done_enabled: false
    transmission_daemon_script_torrent_done_filename: ''
    transmission_daemon_seed_queue_enabled: false
    transmission_daemon_seed_queue_size: 10
    transmission_daemon_speed_limit_down: 100
    transmission_daemon_speed_limit_down_enabled: false
    transmission_daemon_speed_limit_up: 100
    transmission_daemon_speed_limit_up_enabled: false
    transmission_daemon_start_added_torrents: true
    transmission_daemon_trash_original_torrent_files: false
    transmission_daemon_umask: 18
    transmission_daemon_upload_limit: 100
    transmission_daemon_upload_limit_enabled: false
    transmission_daemon_upload_slots_per_torrent: 14
    transmission_daemon_utp_enabled: true

## Dependencies

* [linuxhq.linux.epel](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/epel)

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.transmission_daemon
          transmission_daemon_bind_address_ipv6: "fe80::"
          transmission_daemon_dht_enabled: false
          transmission_daemon_pex_enabled: false
          transmission_daemon_umask: 2

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
