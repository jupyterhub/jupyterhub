"""Test version checking"""
import logging

import pytest

from .._version import _check_version


@pytest.mark.parametrize('hub_version, singleuser_version, log_level, msg', [
    ('0.8.0', '0.8.0', logging.DEBUG, 'both on version'),
    ('0.8.0', '0.8.1', logging.DEBUG, ''),
    ('0.8.0', '0.8.0.dev', logging.DEBUG, ''),
    ('0.8.0', '0.9.0', logging.WARNING, 'This could cause failure to authenticate'),
    ('', '0.8.0', logging.WARNING, 'Hub has no version header'),
    ('0.8.0', '', logging.WARNING, 'Single-user server has no version header'),
])
def test_check_version(hub_version, singleuser_version, log_level, msg, caplog):
    log = logging.getLogger()
    caplog.set_level(logging.DEBUG)
    _check_version(hub_version, singleuser_version, log)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == log_level
    assert msg in record.getMessage()
