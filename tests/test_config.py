import io
from textwrap import dedent
import os
from dask_kubernetes.cli.utils import get_conf, render_templates

import pytest


PKG = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture
def config():
    return io.BytesIO(dedent(b"""\
    cluster:
      num_nodes: 12
    """))


def test_get_conf_default():
    result = get_conf(None, None)
    assert set(result.keys()) == {'cluster', 'jupyter', 'scheduler', 'workers'}


def test_file_overrides(config):
    result = get_conf(config, None)
    assert result['cluster']['num_nodes'] == 12
    assert result['cluster']['zone'] == 'us-east1-b'


def test_cli():
    result = get_conf(None, ['cluster.num_nodes=12'])
    assert result['cluster']['num_nodes'] == '12'  # TODO: types
    assert result['cluster']['zone'] == 'us-east1-b'


def test_cli_overrides(config):
    result = get_conf(None, ['cluster.num_nodes=15'])
    assert result['cluster']['num_nodes'] == '15'
    assert result['cluster']['zone'] == 'us-east1-b'


def test_render_templates():
    config = {
        "jupyter": {"port": 443},
        "scheduler": {},
        "workers": {},
    }
    result = render_templates(config, '')
    # probably want to do some more verification here.
    assert len(result)
