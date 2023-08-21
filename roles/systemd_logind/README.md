# systemd\_logind

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Login manager

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    systemd_logind_handlehibernatekey: hibernate
    systemd_logind_handlehibernatekeylongpress: ignore
    systemd_logind_handlelidswitch: suspend
    systemd_logind_handlelidswitchdocked: ignore
    systemd_logind_handlelidswitchexternalpower: suspend
    systemd_logind_handlepowerkey: poweroff
    systemd_logind_handlepowerkeylongpress: ignore
    systemd_logind_handlerebootkey: reboot
    systemd_logind_handlerebootkeylongpress: poweroff
    systemd_logind_handlesuspendkey: suspend
    systemd_logind_handlesuspendkeylongpress: hibernate
    systemd_logind_hibernatekeyignoreinhibited: false
    systemd_logind_holdofftimeoutsec: 30s
    systemd_logind_idleaction: ignore
    systemd_logind_idleactionsec: 30min
    systemd_logind_inhibitdelaymaxsec: 5
    systemd_logind_inhibitorsmax: 8192
    systemd_logind_killexcludeusers: []
    systemd_logind_killonlyusers: []
    systemd_logind_killuserprocesses: false
    systemd_logind_lidswitchignoreinhibited: true
    systemd_logind_nautovts: 0
    systemd_logind_powerkeyignoreinhibited: false
    systemd_logind_rebootkeyignoreinhibited: false
    systemd_logind_removeipc: false
    systemd_logind_reservevt: 6
    systemd_logind_runtimedirectorysize: 10%
    systemd_logind_runtimedirectoryinodesmax: null
    systemd_logind_sessionsmax: 8192
    systemd_logind_stopidlesessionsec: infinity
    systemd_logind_suspendkeyignoreinhibited: false
    systemd_logind_userstopdelaysec: 10

## Dependencies

None

## Example Playbook

    - hosts: server
      collections:
        - linuxhq.linux
      roles:
        - role: linuxhq.linux.systemd_logind
          systemd_logind_killonlyusers:
            - linuxhq
            - tkimball

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
