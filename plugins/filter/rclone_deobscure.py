# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
name: rclone_deobscure
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.2.0"
short_description: Reveal a password from an obscured rclone value
description:
  - Decodes a value obscured with rclone's published static key, as
    produced by C(rclone obscure) or P(linuxhq.linux.rclone_obscure#filter),
    back to plaintext.
  - An empty string is returned unchanged, unlike C(rclone reveal), which
    rejects it.
  - Other values that rclone would reject, such as those containing
    characters outside the unpadded base64url alphabet, raise an error.
  - A vault encrypted value is decrypted before it is revealed.
positional: _input
options:
  _input:
    description: The obscured value to decode.
    type: string
    required: true
requirements:
  - pycryptodome or pycryptodomex
"""

EXAMPLES = r"""
- name: Ensure rclone password fact is generated
  ansible.builtin.set_fact:
    __rclone_password: "{{ rclone_config_pass | linuxhq.linux.rclone_deobscure }}"
"""

RETURN = r"""
_value:
  description: The plaintext value.
  type: string
"""

from ansible.errors import AnsibleFilterError
from ansible.module_utils.common.text.converters import to_text
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode

from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    deobscure,
)


def rclone_deobscure(obscured):
    if not HAS_PYCRYPTODOME:
        raise AnsibleFilterError("rclone_deobscure requires the pycryptodome library")

    if isinstance(obscured, AnsibleVaultEncryptedUnicode):
        obscured = to_text(obscured)

    try:
        return deobscure(obscured)
    except (TypeError, ValueError) as e:
        raise AnsibleFilterError(f"rclone_deobscure failed: {e}")


class FilterModule:
    def filters(self):
        return {
            "rclone_deobscure": rclone_deobscure,
        }
