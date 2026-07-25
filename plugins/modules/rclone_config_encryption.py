# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: rclone_config_encryption
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.2.7
short_description: Manage rclone configuration file encryption
description:
  - Encrypt or decrypt an rclone configuration file in place, using the same
    C(RCLONE_ENCRYPT_V0) envelope that C(rclone config encryption set) writes.
  - The configuration key is the SHA256 digest of the NFKC normalized password,
    and the body is sealed with XSalsa20-Poly1305, so rclone reads back what this
    module writes and the module reads back what rclone writes.
  - The module is idempotent. An already encrypted file that opens with O(password)
    is left untouched, as is an already decrypted one, so no needless rewrite
    churns the ciphertext.
  - Neither the password nor the decrypted configuration is ever placed on a
    command line or returned to the controller.
options:
  password:
    description:
      - Password securing the configuration file.
      - Used to encrypt when O(state=present) and to decrypt when O(state=absent).
      - Whitespace is significant and is not stripped, matching rclone. A password
        that is empty or entirely whitespace is rejected.
    type: str
    required: true
  path:
    description:
      - Path to the rclone configuration file to encrypt or decrypt.
      - The file must already exist.
    type: path
    required: true
  state:
    description:
      - V(present) encrypts the configuration file, leaving an already encrypted
        file alone when it opens with O(password).
      - V(absent) decrypts the configuration file, leaving an already decrypted
        file alone.
    type: str
    choices:
      - absent
      - present
    default: present
extends_documentation_fragment:
  - ansible.builtin.files
requirements:
  - pycryptodome
"""

EXAMPLES = r"""
- name: Ensure rclone configuration is encrypted
  linuxhq.linux.rclone_config_encryption:
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: present

- name: Ensure rclone configuration is encrypted with strict ownership
  linuxhq.linux.rclone_config_encryption:
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: present
    group: root
    mode: '0600'
    owner: root

- name: Ensure rclone configuration is decrypted
  linuxhq.linux.rclone_config_encryption:
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: absent
"""

RETURN = r"""
encrypted:
  description: Whether the configuration file is encrypted after the run.
  returned: always
  type: bool
  sample: true
path:
  description: Path to the managed configuration file.
  returned: always
  type: str
  sample: /root/.config/rclone/rclone.conf
"""

import os
import tempfile

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text
from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    decrypt_config,
    encrypt_config,
    is_encrypted,
)


def read_config(module):
    path = module.params["path"]

    if not os.path.exists(path):
        module.fail_json(msg="configuration file does not exist: %s" % path)

    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except IOError as error:
        module.fail_json(msg="unable to read %s: %s" % (path, to_native(error)))

    return raw, to_text(raw, errors="replace")


def discard_file(path):
    if not os.path.exists(path):
        return

    if hasattr(os, "chflags"):
        try:
            os.chflags(path, 0)
        except OSError:
            pass

    try:
        os.remove(path)
    except OSError:
        pass


def write_config(module, content):
    path = module.params["path"]
    tmp = None

    try:
        handle, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")

        with os.fdopen(handle, "wb") as stream:
            stream.write(to_bytes(content))
            stream.flush()
            os.fsync(stream.fileno())

        module.atomic_move(tmp, path)
    except Exception as error:
        module.fail_json(msg="unable to write %s: %s" % (path, to_native(error)))
    finally:
        if tmp is not None:
            discard_file(tmp)


def ensure_present(module):
    raw, text = read_config(module)
    password = module.params["password"]

    try:
        encrypted = is_encrypted(text)
    except ValueError as error:
        module.fail_json(msg=to_native(error))

    if encrypted:
        if decrypt_config(text, password) is None:
            module.fail_json(
                msg="configuration file is already encrypted with a different password"
            )

        changed = module.set_fs_attributes_if_different(
            module.load_file_common_arguments(module.params), False
        )

        module.exit_json(changed=changed, encrypted=True, path=module.params["path"])

    if not module.check_mode:
        write_config(module, encrypt_config(raw, password))

    changed = module.set_fs_attributes_if_different(
        module.load_file_common_arguments(module.params), True
    )

    module.exit_json(changed=changed, encrypted=True, path=module.params["path"])


def ensure_absent(module):
    dummy, text = read_config(module)
    password = module.params["password"]

    try:
        encrypted = is_encrypted(text)
    except ValueError as error:
        module.fail_json(msg=to_native(error))

    if not encrypted:
        changed = module.set_fs_attributes_if_different(
            module.load_file_common_arguments(module.params), False
        )

        module.exit_json(changed=changed, encrypted=False, path=module.params["path"])

    plaintext = decrypt_config(text, password)

    if plaintext is None:
        module.fail_json(msg="unable to decrypt configuration file, wrong password")

    if not module.check_mode:
        write_config(module, plaintext)

    changed = module.set_fs_attributes_if_different(
        module.load_file_common_arguments(module.params), True
    )

    module.exit_json(changed=changed, encrypted=False, path=module.params["path"])


def main():
    argument_spec = dict(
        password={"type": "str", "required": True, "no_log": True},
        path={"type": "path", "required": True},
        state={"type": "str", "choices": ["absent", "present"], "default": "present"},
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        add_file_common_args=True,
        supports_check_mode=True,
    )

    if not HAS_PYCRYPTODOME:
        module.fail_json(msg=missing_required_lib("pycryptodome"))

    if not module.params["password"].strip():
        module.fail_json(msg="no characters in password")

    if module.params["state"] == "present":
        ensure_present(module)

    ensure_absent(module)


if __name__ == "__main__":
    main()
