
import os
import sys
from unittest import mock
from certipy import Certipy
import pytest

from jupyterhub.tests.mocking import MockHub

from .utils import async_requests

def create_external_ca_and_signed_cert(tmpdir):
    """Create an external CA and a signed certificate for testing using certipy"""
    certipy = Certipy(store_dir=str(tmpdir))
    certipy.create_ca("external-ca", overwrite=True)
    signed = certipy.create_signed_pair(
        "external", "external-ca", overwrite=True, alt_names=["DNS:localhost", "IP:127.0.0.1"]
    )
    return signed["files"]

@pytest.fixture(scope='module')
async def app_with_external_ca(request, ssl_tmpdir):
    """Mock a jupyterhub app for testing"""
    mocked_app = None
    kwargs = dict()
    kwargs.update(dict(internal_ssl=True, internal_certs_location=str(ssl_tmpdir)))    
    external_certs = create_external_ca_and_signed_cert(ssl_tmpdir)
    kwargs.update(dict(external_ssl_authorities={"external-ca": external_certs}))
    
    mocked_app = MockHub.instance(**kwargs)

    def fin():
        # disconnect logging during cleanup because pytest closes captured FDs prematurely
        mocked_app.log.handlers = []
        MockHub.clear_instance()
        try:
            mocked_app.stop()
        except Exception as e:
            print(f"Error stopping Hub: {e}", file=sys.stderr)

    request.addfinalizer(fin)
    await mocked_app.initialize([])
    await mocked_app.start()
    return mocked_app

async def test_connection_hub_with_external_ssl_authority(app_with_external_ca):
    """Test that JupyterHub trusts certificates signed by external SSL authorities

    This verifies the fix for issue #5289: external_ssl_authorities should be
    included in the internal trust bundles so that the hub trusts external CAs.
    """

    assert 'external-ca' in app_with_external_ca.internal_ssl_authorities
    assert 'external-ca' in app_with_external_ca.internal_ssl_components_trust['hub-ca']

    cert = (app_with_external_ca.external_certs["files"]["cert"], app_with_external_ca.external_certs["files"]["key"])
    r = await async_requests.get(app_with_external_ca.hub.url, cert=cert, verify=app_with_external_ca.internal_trust_bundles['hub-ca'])
    r.raise_for_status()