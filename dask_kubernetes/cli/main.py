#!/usr/bin/env python

import click
import logging
from math import ceil
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import webbrowser

from .config import setup_logging
from .utils import (call, check_output, required_commands, get_conf,
                    render_templates, write_templates)


logger = logging.getLogger(__name__)


def start():
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
@click.argument("settings_file", default=None, required=False)
@click.option('--set', '-s', multiple=True,
              help="Additional key-value pairs to fill in the template.")
def create(ctx, name, settings_file, set):
    conf = get_conf(settings_file, set)
    zone = conf['cluster']['zone']
    call("gcloud config set compute/zone {0}".format(zone))
    call("gcloud config set compute/region {0}".format(zone.rsplit('-', 1)[0]))
    call("gcloud container clusters create {0} --num-nodes {1} --machine-type"
         " {2} --no-async --disk-size {3} --tags=dask --scopes "
         "https://www.googleapis.com/auth/cloud-platform".format(
            name, conf['cluster']['num_nodes'], conf['cluster']['machine_type'],
            conf['cluster']['disk_size']))
    try:
        subprocess.check_call("gcloud container clusters get-credentials {0}".
                              format(name), shell=True)
    except:
        raise RuntimeError('Cluster creation failed!')
    par = pardir(name)
    shutil.rmtree(par, True)
    print("Copying template config to ", par)
    os.makedirs(par, exist_ok=True)  # not PY2 ?
    write_templates(render_templates(conf, par))
    call("kubectl create -f {0}  --save-config".format(par))


@cli.command(short_help='Update config from parameter files')
@click.pass_context
@click.argument('cluster', required=True)
def update_config(ctx, cluster):
    context = get_context_from_cluster(cluster)
    par = pardir(cluster)
    call("kubectl --context {} apply -f {}".format(context, par))


def pardir(cluster):
    return os.sep.join([os.path.expanduser('~'), '.dask', 'kubernetes',
                        cluster])


@cli.command(short_help="Reset kubernetes values from file or command line "
                        "and apply")
@click.pass_context
@click.argument('name', required=True)
@click.argument("settings_file", default=None, required=False)
@click.argument('args', nargs=-1)
def rerender(ctx, cluster, settings_file, args):
    conf = get_conf(settings_file, args)
    par = pardir(cluster)
    # TODO: apply num_nodes change
    write_templates(render_templates(conf, par))
    update_config(ctx, cluster)


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


@resize.command("both",
                short_help="Resize the number of pods in a cluster,"
                           " and resize number of nodes proportionately")
@click.pass_context
@click.argument('cluster', required=True)
@click.argument('value', required=True)
def both(ctx, cluster, value):
    value = int(value)
    context = get_context_from_cluster(cluster)
    n, p = counts(cluster)
    call("gcloud container clusters resize {0} --size {1} --async".format(
        cluster, ceil(n * value/p)))
    call("kubectl --context {0} scale rc dask-worker --replicas {1}".format(
        context, value))


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
Config directory:  {par}

To connect to scheduler inside of cluster
-----------------------------------------
from dask.distributed import Client
c = Client('dask-scheduler:8786')

or from outside the cluster

c = Client('{scheduler}:8786')
"""
    context = get_context_from_cluster(cluster)
    jupyter, scheduler = services_in_context(context)
    par = pardir(cluster)
    print(template.format(jupyter=jupyter, scheduler=scheduler, par=par))


def services_in_context(context):
    out = check_output("kubectl --context {0} get services".format(context))
    for line in out.split('\n'):
        words = line.split()
        if words and words[0] == 'jupyter-notebook':
            jupyter = words[2]
        if words and words[0] == 'dask-scheduler':
            scheduler = words[2]
    return jupyter, scheduler


def counts(cluster):
    context = get_context_from_cluster(cluster)
    out = check_output('gcloud container clusters describe {}'.format(cluster))
    nodes = int(re.search('currentNodeCount: (\d+)', out).groups()[0])
    out = check_output(
        'kubectl --context {} get rc dask-worker'.format(context))
    lines = [o for o in out.split('\n') if o.startswith('dask-worker')]
    pods = int(lines[0].split()[1])
    return nodes, pods


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


@cli.command(short_help='Open the dask status dashboard in the browser')
@click.pass_context
@click.argument('cluster', required=True)
def status(ctx, cluster):
    context = get_context_from_cluster(cluster)
    jupyter, scheduler = services_in_context(context)
    webbrowser.open('http://{}:8787/status'.format(scheduler))


@cli.command(short_help="Delete a cluster.")
@click.pass_context
@click.argument('name', required=True)
def delete(ctx, name):
    call("gcloud container clusters delete {0}".format(name))


if __name__ == '__main__':
    start()
