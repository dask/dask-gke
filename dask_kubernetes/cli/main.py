#!/usr/bin/env python

import logging

from .. import __version__
from .config import setup_logging
from .utils import call, required_commands

import click

logger = logging.getLogger(__name__)


def start():
    import sys
    import logging
    import traceback

    try:
        setup_logging(logging.DEBUG)
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("Interrupted by Ctrl-C.")
        sys.exit(1)
    except Exception:
        click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(prog_name="dask-kubernetes", version=__version__)
@click.pass_context
@required_commands("gcloud", "kubectl")
def cli(ctx):
    """
    Create and manage Dask clusters on Kubernetes.
    """
    ctx.obj = {}


@cli.command(short_help="Create a cluster.")
@click.pass_context
@click.argument('name', required=True)
@click.option("--num-nodes",
              default=6,
              show_default=True,
              required=False,
              help="The number of nodes to be created in the cluster.")
@click.option("--disk-size",
              default=50,
              show_default=True,
              required=False,
              help="Size in GB for node VM boot disks.")
@click.option("--machine-type", "-m",
              default="n1-standard-4",
              show_default=True,
              required=False,
              help="The type of machine to use for nodes.")
@click.option("--zone", "-z",
              default="us-east1-b",
              show_default=True,
              required=False,
              help="The compute zone for the cluster.")
@click.option("--filename", "-f",
              default="kubernetes",
              show_default=True,
              required=False,
              help="Filename, directory, or URL to files to use to create the resource")
def create(ctx, name, num_nodes, machine_type, disk_size, zone, filename):
    call("gcloud config set compute/zone {0}".format(zone))
    call("gcloud container clusters create {0} --num-nodes {1} --machine-type {2} --no-async --disk-size {3} --tags=dask,anacondascale".format(name, num_nodes, machine_type, disk_size))
    call("gcloud container clusters get-credentials {0}".format(name))
    call("kubectl create -f {0}".format(filename))


@cli.command(short_help="Resize a cluster.")
@click.pass_context
@click.argument('name', required=True)
@click.argument('size', required=True)
def resize(ctx, name, size):
    call("gcloud container clusters resize {0} --size {1} --async".format(name, size))


@cli.command(short_help="Show all clusters.")
@click.pass_context
def list(ctx):
    call("gcloud container clusters list")


@cli.command(short_help="Delete a cluster.")
@click.pass_context
@click.argument('name', required=True)
def delete(ctx, name):
    call("gcloud container clusters delete {0}".format(name))


if __name__ == '__main__':
    start()
