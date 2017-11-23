"""Test version checking"""
import logging

import pytest

from .._version import _check_version


@pytest.mark.parametrize('hub_version, singleuser_version, log_level, msg', [
    ('0.8.0', '0.8.0', logging.DEBUG, 'both on version'),
])
def test_check_version(hub_version, singleuser_version, log_level, msg, caplog):
    log = logging.getLogger()
    caplog.set_level(logging.DEBUG)
    _check_version(hub_version, singleuser_version, log)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == log_level
    assert msg in record.getMessage()

