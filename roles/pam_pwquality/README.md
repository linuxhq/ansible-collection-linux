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
          pam_pwquality_difok: 8
          pam_pwquality_gecoscheck: 1
          pam_pwquality_lcredit: -1
          pam_pwquality_maxrepeat: 4
          pam_pwquality_maxclassrepeat: 4
          pam_pwquality_minclass: 4
          pam_pwquality_minlen: 15
          pam_pwquality_ocredit: -1
          pam_pwquality_ucredit: -1
