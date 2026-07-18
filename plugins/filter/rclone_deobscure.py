# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
name: rclone_deobscure
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.2.6
short_description: Reveal a password from an obscured rclone value
description:
  - Decodes a value obscured with rclone's published static key, as
    produced by C(rclone obscure) or P(linuxhq.linux.rclone_obscure#filter),
    back to plaintext.
  - Values that rclone would reject, such as those containing characters
    outside the unpadded base64url alphabet, raise an error.
positional: _input
options:
  _input:
    description: The obscured value to decode.
    type: string
    required: true
requirements:
  - pycryptodome
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

from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    deobscure,
)


def rclone_deobscure(obscured):
    if not HAS_PYCRYPTODOME:
        raise AnsibleFilterError("rclone_deobscure requires the pycryptodome library")

    try:
        return deobscure(obscured)
    except Exception as e:
        raise AnsibleFilterError("rclone_deobscure failed: %s" % e)


class FilterModule(object):
    def filters(self):
        return {
            "rclone_deobscure": rclone_deobscure,
        }
