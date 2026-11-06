import pytest

from voxwire.core import store


@pytest.fixture(autouse=True, scope="session")
def _isolated_call_log(tmp_path_factory):
    store.reset(str(tmp_path_factory.mktemp("data")))
