# kmod\_tpe

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Trusted Path Execution Linux Kernel Module

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    kmod_tpe_admin_gid: 0
    kmod_tpe_check_file: true
    kmod_tpe_dmz_gid: 0
    kmod_tpe_exec_whitelist: []
    kmod_tpe_extras_harden_ptrace: true
    kmod_tpe_extras_hide_uname: false
    kmod_tpe_extras_ignore_softmode: false
    kmod_tpe_extras_log: true
    kmod_tpe_extras_lsmod: true
    kmod_tpe_extras_proc_kallsyms: true
    kmod_tpe_extras_ps: false
    kmod_tpe_extras_ps_gid: 0
    kmod_tpe_extras_restrict_setuid: false
    kmod_tpe_group_writable: true
    kmod_tpe_hardcoded_path: []
    kmod_tpe_kernel_dmesg_restrict: true
    kmod_tpe_kernel_modules_disabled: false
    kmod_tpe_lsmod_whitelist:
      - /usr/bin/gnome-control-center
      - /usr/bin/gnome-shell
      - /usr/lib64/firefox/firefox
      - /usr/lib64/thunderbird/thunderbird
    kmod_tpe_kill: false
    kmod_tpe_lock: false
    kmod_tpe_log: true
    kmod_tpe_log_floodburst: 5
    kmod_tpe_log_floodtime: 5
    kmod_tpe_log_max: 50
    kmod_tpe_log_verbose: true
    kmod_tpe_mmap_whitelist:
      - /usr/bin/cheese
      - /usr/bin/empathy-accounts
      - /usr/bin/gedit
      - /usr/bin/gjs-console
      - /usr/bin/glxinfo
      - /usr/bin/glxgears
      - /usr/bin/gnome-contacts
      - /usr/bin/gnome-control-center
      - /usr/bin/gnome-session
      - /usr/bin/gnome-shell
      - /usr/bin/ibus-daemon
      - /usr/bin/kinfocenter
      - /usr/bin/knotify4
      - /usr/bin/kwin
      - /usr/bin/pulseaudio
      - /usr/bin/seahorse
      - /usr/bin/totem
      - /usr/bin/virt-manager
      - /usr/bin/yelp
      - /usr/lib64/firefox/firefox
      - /usr/lib64/libreoffice/program/soffice.bin
      - /usr/lib64/thunderbird/thunderbird
      - /usr/libexec/gnome-initial-setup
      - /usr/libexec/gnome-session-check-accelerated-helper
      - /usr/libexec/kde4/kwin_opengl_test
    kmod_tpe_mprotect_whitelist: []
    kmod_tpe_paranoid: false
    kmod_tpe_ptrace_whitelist: []
    kmod_tpe_setuid_whitelist: []
    kmod_tpe_softmode: false
    kmod_tpe_strict: true
    kmod_tpe_trusted_apps: []
    kmod_tpe_trusted_gid: 0
    kmod_tpe_trusted_invert: false
    kmod_tpe_uname_whitelist: []
    kmod_tpe_xattr_soften: true

## Dependencies

* [linuxhq.linux.elrepo](https://github.com/linuxhq/ansible-collection-linux/tree/main/roles/elrepo)

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.kmod_tpe
          kmod_tpe_softmode: true

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
