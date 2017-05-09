#!/usr/bin/env python

import click
import logging
import os
import subprocess
import time
import webbrowser

from .config import setup_logging
from .utils import call, check_output, required_commands


logger = logging.getLogger(__name__)
filename = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        '../kubernetes'))


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
@click.version_option(prog_name="dask-kubernetes", version="0.0.1")
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
def create(ctx, name, num_nodes, machine_type, disk_size, zone):
    call("gcloud config set compute/zone {0}".format(zone))
    call("gcloud container clusters create {0} --num-nodes {1} --machine-type"
         " {2} --no-async --disk-size {3} --tags=dask,anacondascale".format(
            name, num_nodes, machine_type, disk_size))
    call("gcloud container clusters get-credentials {0}".format(name))
    print(filename)
    call("kubectl create -f {0}".format(filename))


@cli.group('resize', short_help="Resize a cluster.")
def resize():
    pass


@resize.command("nodes", short_help="Resize the number of nodes in a cluster.")
@click.pass_context
@click.argument('cluster', required=True)
@click.argument('value', required=True)
def nodes(ctx, cluster, value):
    call("gcloud container clusters resize {0} --size {1} --async".format(
        cluster, value))


def get_context_from_cluster(cluster):
    """
    Returns context for a cluster.
    """
    output = check_output("kubectl config get-contexts -o name")
    contexts = output.strip().split('\n')
    for context in contexts:
        # Each context uses the format: gke_{PROJECT}_{ZONE}_{CLUSTER}
        if context.split('_')[-1] == cluster:
            return context
    return None


@resize.command("pods", short_help="Resize the number of pods in a cluster.")
@click.pass_context
@click.argument('cluster', required=True)
@click.argument('value', required=True)
def pods(ctx, cluster, value):
    context = get_context_from_cluster(cluster)
    call("kubectl --context {0} scale rc dask-worker --replicas {1}".format(
        context, value))


@cli.command(short_help="Show all clusters.")
@click.pass_context
def list(ctx):
    call("gcloud container clusters list")


@cli.command(short_help='Detailed info about your running  dask cluster')
@click.pass_context
@click.argument('cluster', required=True)
def info(ctx, cluster):
    template = """Addresses
---------
   Web Interface:  http://{scheduler}:8787/status
Jupyter Notebook:  http://{jupyter}:8888

To connect to scheduler inside of cluster
-----------------------------------------
from dask.distributed import Client
c = Client('dask-scheduler:8786')
"""
    context = get_context_from_cluster(cluster)
    jupyter, scheduler = services_in_context(context)
    print(template.format(jupyter=jupyter, scheduler=scheduler))


def services_in_context(context):
    out = check_output("kubectl --context {0} get services".format(context))
    for line in out.split('\n'):
        words = line.split()
        if words and words[0] == 'jupyter-notebook':
            jupyter = words[2]
        if words and words[0] == 'dask-scheduler-status':
            scheduler = words[2]
    return jupyter, scheduler


@cli.command(short_help='Open the remote kubernetes console in the browser')
@click.pass_context
@click.argument('cluster', required=True)
def dashboard(ctx, cluster):
    context = get_context_from_cluster(cluster)
    try:
        P = subprocess.Popen('kubectl --context {0} proxy'.format(
            context).split())
        webbrowser.open('http://localhost:8001/ui')
        print('\nProxy running - press ^C to exit')
        while True:
            time.sleep(100)
    finally:
        P.terminate()


@cli.command(short_help='Open the remote jupyter notebook in the browser')
@click.pass_context
@click.argument('cluster', required=True)
def notebook(ctx, cluster):
    context = get_context_from_cluster(cluster)
    jupyter, scheduler = services_in_context(context)
    webbrowser.open('http://{}:8888'.format(jupyter))


@cli.command(short_help="Delete a cluster.")
@click.pass_context
@click.argument('name', required=True)
def delete(ctx, name):
    call("gcloud container clusters delete {0}".format(name))


if __name__ == '__main__':
    start()
