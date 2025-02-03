# pam\_pwquality

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Password creation requirements

## Requirements

None

## Role Variables

    pam_pwquality_badwords: []
    pam_pwquality_dcredit: 0
    pam_pwquality_dictcheck: 1
    pam_pwquality_dictpath: null
    pam_pwquality_difok: 1
    pam_pwquality_enforce_for_root: false
    pam_pwquality_enforcing: 1
    pam_pwquality_gecoscheck: 0
    pam_pwquality_lcredit: 0
    pam_pwquality_local_users_only: false
    pam_pwquality_maxclassrepeat: 0
    pam_pwquality_maxrepeat: 0
    pam_pwquality_maxsequence: 0
    pam_pwquality_minclass: 0
    pam_pwquality_minlen: 8
    pam_pwquality_ocredit: 0
    pam_pwquality_retry: 1
    pam_pwquality_ucredit: 0
    pam_pwquality_usercheck: 1
    pam_pwquality_usersubstr: 0

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.pam_pwquality
          pam_pwquality_dcredit: -1
          pam_pwquality_lcredit: -1
          pam_pwquality_ocredit: -1
          pam_pwquality_ucredit: -1
          pam_pwquality_gecoscheck: 1
          pam_pwquality_enforce_for_root: true
          pam_pwquality_maxrepeat: 3
          pam_pwquality_minlen: 16

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
