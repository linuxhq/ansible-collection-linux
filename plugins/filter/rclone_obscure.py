# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
name: rclone_obscure
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.2.0"
short_description: Obscure a password for an rclone configuration
description:
  - Encrypts a plaintext value with rclone's published static key and
    encodes it for use as an obscured rclone configuration value.
  - Output is accepted anywhere C(rclone obscure) output is, but the
    initialization vector is derived from the input so repeated runs
    produce identical output and stay idempotent.
  - Obscuring is reversible encoding, not secure encryption; treat
    obscured values as secrets.
  - An empty string is returned unchanged rather than obscured, unlike
    C(rclone obscure), which returns a non-empty value for it.
  - A vault encrypted value is decrypted before it is obscured.
  - Values that are not strings or bytes raise an error.
  - Text is obscured as its UTF-8 bytes. U+DC80 to U+DCFF, which Ansible uses
    for bytes that are not valid UTF-8, such as from the b64decode filter,
    are obscured as those bytes, as C(rclone obscure) accepts them. Any other
    lone surrogate code point, from U+D800 to U+DC7F, is not valid UTF-8 and
    raises an error.
positional: _input
options:
  _input:
    description: The plaintext value to obscure.
    type: string
    required: true
requirements:
  - pycryptodome >= 3.7.0 or pycryptodomex >= 3.7.0
"""

EXAMPLES = r"""
- name: Ensure rclone is configured with an sftp remote
  ansible.builtin.include_role:
    name: linuxhq.linux.rclone
  vars:
    rclone_config:
      - name: backup
        type: sftp
        host: backup.example.com
        user: backup
        pass: "{{ vault_sftp_password | linuxhq.linux.rclone_obscure }}"
"""

RETURN = r"""
_value:
  description: The obscured value.
  returned: success
  type: string
"""

from ansible.errors import AnsibleFilterError

from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    obscure,
)


def rclone_obscure(plaintext):
    if not HAS_PYCRYPTODOME:
        raise AnsibleFilterError("rclone_obscure requires the pycryptodome or pycryptodomex library")

    try:
        return obscure(plaintext)
    except (TypeError, ValueError) as e:
        raise AnsibleFilterError(f"rclone_obscure failed: {e}")


class FilterModule:
    def filters(self):
        return {
            "rclone_obscure": rclone_obscure,
        }
