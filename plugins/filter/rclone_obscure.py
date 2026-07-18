# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
name: rclone_obscure
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.2.6
short_description: Obscure a password for an rclone configuration
description:
  - Encrypts a plaintext value with rclone's published static key and
    encodes it for use as an obscured rclone configuration value.
  - Output is accepted anywhere C(rclone obscure) output is, but the
    initialization vector is derived from the input so repeated runs
    produce identical output and stay idempotent.
  - Obscuring is reversible encoding, not secure encryption; treat
    obscured values as secrets.
positional: _input
options:
  _input:
    description: The plaintext value to obscure.
    type: string
    required: true
requirements:
  - pycryptodome
"""

EXAMPLES = r"""
- name: Ensure rclone config pass fact is generated
  ansible.builtin.set_fact:
    __rclone_config_pass: "{{ rclone_password | linuxhq.linux.rclone_obscure }}"
"""

RETURN = r"""
_value:
  description: The obscured value.
  type: string
"""

from ansible.errors import AnsibleFilterError

from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    obscure,
)


def rclone_obscure(plaintext):
    if not HAS_PYCRYPTODOME:
        raise AnsibleFilterError("rclone_obscure requires the pycryptodome library")

    try:
        return obscure(plaintext)
    except Exception as e:
        raise AnsibleFilterError("rclone_obscure failed: %s" % e)


class FilterModule(object):
    def filters(self):
        return {
            "rclone_obscure": rclone_obscure,
        }
