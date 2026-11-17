# kopia

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)

Fast and secure open-source backup software

## Requirements

None

## Role Variables

    kopia_maintenance: {}
    kopia_packages:
      - kopia
    kopia_password: kopia
    kopia_policies: []
    kopia_repository: {}
    kopia_server_args:
      - --address=127.0.0.1:51515
      - --disable-csrf-token-checks
      - --insecure
      - --no-check-for-updates
      - --without-password
    kopia_snapshot: false

Each `kopia_policies` item manages the policy of one target with
`linuxhq.linux.kopia_policy`:

    kopia_policies:
      - target: /home/vagrant   # required, a path, user@host, user@host:/path or (global)
        policy: {}              # the complete policy, required when state is present
        state: present          # present (default) or absent

With `kopia_snapshot: true`, the role takes a new snapshot of each target
that starts with `/` and whose `state` is `present` on every run, which is not
idempotent. Targets such as `(global)` or `user@host:/path`, and targets with
`state: absent`, are not snapshotted.

## Dependencies

None

## Example Playbook

    - hosts: server
      roles:
        - role: linuxhq.linux.kopia
          kopia_password: "{{ vault_kopia_password }}"

          kopia_repository:
            storage: filesystem
            options:
              path: /srv/kopia

          kopia_maintenance:
            enable_full: true
            enable_quick: true
            full_interval: 86400
            quick_interval: 3600

          kopia_policies:
            - target: /home/vagrant
              policy:
                compression:
                  compressor_name: gzip
                files:
                  ignore:
                    - '*.log'
                    - '*.tmp'
                    - .cache/
                retention:
                  keep_annual: 0
                  keep_hourly: 24
                  keep_latest: 2
                  keep_monthly: 3
                  keep_weekly: 4
                scheduling:
                  interval_seconds: 3600
