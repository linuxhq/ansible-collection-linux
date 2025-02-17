# logind

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Login manager

## Requirements

None

## Role Variables

    logind_handlehibernatekey: hibernate
    logind_handlehibernatekeylongpress: ignore
    logind_handlelidswitch: suspend
    logind_handlelidswitchdocked: ignore
    logind_handlelidswitchexternalpower: suspend
    logind_handlepowerkey: poweroff
    logind_handlepowerkeylongpress: ignore
    logind_handlerebootkey: reboot
    logind_handlerebootkeylongpress: poweroff
    logind_handlesuspendkey: suspend
    logind_handlesuspendkeylongpress: hibernate
    logind_hibernatekeyignoreinhibited: false
    logind_holdofftimeoutsec: 30s
    logind_idleaction: ignore
    logind_idleactionsec: 30min
    logind_inhibitdelaymaxsec: 5
    logind_inhibitorsmax: 8192
    logind_killexcludeusers:
      - root
    logind_killonlyusers: []
    logind_killuserprocesses: false
    logind_lidswitchignoreinhibited: true
    logind_nautovts: 6
    logind_powerkeyignoreinhibited: false
    logind_rebootkeyignoreinhibited: false
    logind_removeipc: true
    logind_reservevt: 6
    logind_runtimedirectorysize: 10%
    logind_runtimedirectoryinodesmax: null
    logind_sessionsmax: 8192
    logind_stopidlesessionsec: infinity
    logind_suspendkeyignoreinhibited: false
    logind_userstopdelaysec: 10

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.logind
          logind_killonlyusers:
            - vagrant

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
