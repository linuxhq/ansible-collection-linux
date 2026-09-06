from unittest.mock import Mock

import pytest

from ansible.module_utils import basic


class ModuleResult(Exception):
    def __init__(self, values):
        super().__init__(values)
        self.values = values


def exit_json(self, **values):
    raise ModuleResult(values)


def fail_json(self, **values):
    raise ModuleResult({**values, "failed": True})


@pytest.fixture
def run_module(monkeypatch, tmp_path):
    """Run real argument validation and capture module results without a subprocess."""
    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)
    monkeypatch.setattr(
        basic.AnsibleModule, "run_command", Mock(side_effect=AssertionError("unexpected external command"))
    )

    def run(plugin, params=None, check_mode=False):
        args = dict(params or {}, _ansible_check_mode=check_mode, _ansible_remote_tmp=str(tmp_path))
        monkeypatch.setattr(basic, "_load_params", lambda: args)
        with pytest.raises(ModuleResult) as caught:
            plugin.main()

        return caught.value.values

    return run


@pytest.fixture
def module_factory(tmp_path):
    def create(params=None, check_mode=False, diff=False):
        module = Mock(params=params or {}, check_mode=check_mode, _diff=diff, tmpdir=str(tmp_path))
        module.exit_json.side_effect = lambda **values: exit_json(module, **values)
        module.fail_json.side_effect = lambda **values: fail_json(module, **values)
        module.run_command.side_effect = AssertionError("unexpected external command")
        return module

    return create


@pytest.fixture
def invoke():
    def call(function, *args):
        with pytest.raises(ModuleResult) as caught:
            function(*args)

        return caught.value.values

    return call
