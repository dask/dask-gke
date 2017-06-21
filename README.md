# Kubernetes provisioning of a Dask Distributed cluster

This repo hosts some sample configuration to set up Kubernetes containerized
environments for interactive cluster computing in Python with [Jupyter
notebook](http://jupyter.org/) [dask](http://dask.pydata.org/)
and other tools from the PyData and SciPy
ecosystems.

*This is a work in progress*

The Kubernetes API is provided as a hosted service by:

- [Google Container Engine](https://cloud.google.com/container-engine/)
- [OpenShift by Red Hat](https://www.openshift.com/)

Alternatively it is possible to [install and manage Kubernetes by
your-self](http://kubernetes.io/docs/getting-started-guides/).

We will briefly describe usage assuming Google Container Engine (GCE)

## The dask-kubernetes image

The `Dockerfile` file in this repo can be used to build a docker image
with all the necessary tools to run our cluster, in particular:

- `conda` and `pip` to install additional tools and libraries,
- `jupyter` for the notebook interface accessed from any web browser,
- `dask` and its `distributed` scheduler,
- `psutil` and `bokeh` (useful for the [cluster monitoring web interface](
   https://distributed.readthedocs.io/en/latest/web.html))
- many convenient numerical libraries
- interfaces to S3 and GCS medium-term storage solutions

This image will be used to run 3 types of services:

- the `jupyter notebook` server, protected by password `jupyter`. This password is defined
in conf/jupyter_notebook_config.py; to change it, you will need to rebuild this image
and point the kubernetes definitions to the new version.
- the `dask-scheduler` service,
- one `dask-worker` per container in the compute cluster.


### Setup with Google Container Engine

You will need to install the following:

- [gcloud](https://cloud.google.com/sdk/gcloud/) for authentication and
  launching clusters
- [kubectl](https://kubernetes.io/docs/tasks/kubectl/install/) for interacting
  with the kubernetes driver.

Register on the [Google Cloud Platform](https://cloud.google.com/), setup a
billing account and create a project with the Google Compute Engine API enabled.

Ensure that your client SDK is up to date:

```
$ gcloud components update
```

Install `dask-kubernetes` CLI via:

```
$ python setup.py install
```

## Usage


Default settings for the cluster are stored in
[defaults.yaml](dask_kubernetes/cli/defaults.yaml)

The easiest way to customize the cluster to your own purposes is to make
a copy of this file, edit it, and supply it on the command line. The settings
used for a new cluster are a combination of the built-in settings, any
new values in a supplied file, and command-line options

To launch with default values only (where NAME is the label for the cluster):

```bash
dask-kubernetes create NAME
```

To launch with a provided file:

```bash
dask-kubernetes create NAME settings.yaml
```

To launch with a single override parameter

```bash
dask-kubernetes create -s jupyter.port=443 NAME
```

By default, the process will block until done, and then print details
about the created cluster to the screen, including the addresses of
the dask-scheduler, the jupyter notebook, and the Bokeh status monitor.
This same information can be retrieved again with the `info` command.
Most users will want to navigate to the notebook first, which can also
be achieved by calling

```bash
dask-kubernetes notebook NAME
```

and similarly, the `status` command opens the cluster status page.

From within the cluster, you can connect to the distributed scheduler by doing the
following:

```python
from dask.distributed import Client
c = Client('dask-scheduler:8786')
```


When you are done, delete the cluster with the following:

```bash
dask-kubernetes delete NAME
```

(requests confirmation).


## Extras

`dask-kubernetes` work by calling `kubectl`. For those who want finer control
or to investigate the state of the cluster, `kubectl` commands can be
entered on the command line as for any other Kubernetes cluster. Furthermore,
the Kubernetes dashboard is available using

```bash
dask-kubernetes dashboard NAME
```

(note that, unlike the other commands which open browser tabs, this command
is blocking on the command line, since it needs to maintain a proxy connection.)

### Resize cluster

The dask workers live within containers on Google virtual machines. To get more processing
power and memory, you must both increase the number of machines and the number of containers.

To add machines to the cluster, you may do the following

```bash
dask-kubernetes resize nodes NAME COUNT
```

(of course, the more machines, the higher the bill will be)

To add worker containers, you may do the following

```bash
dask-kubernetes resize pods NAME COUNT
```

or resize both while keeping the workers:nodes ratio constant

```bash
dask-kubernetes resize both NAME COUNT
```

(you give the new number of workers requested).


Note that if you allocate more resources than your cluster can
handle, some pods will not start; even if you use auto-scaling, additional
nodes are only launched when CPU usage on existing nodes rises.
To enable auto-scaling, change the appropriate line in `defaults.yaml` or run:
```bash
dask-kubernetes NAME -s cluster.autoscaling=True -s cluster.min_nodes=MIN -s cluster.max_nodes=MAX
```

To see the state of the worker pods, use `kubectl` or the Kubernetes dashboard.

### Logs

we can get the logs of a specific pod with `kubectl logs`:

```
$ kubectl logs -f dask-scheduler-hebul
distributed.scheduler - INFO - Scheduler at:       10.115.249.189:8786
distributed.scheduler - INFO -      http at:       10.115.249.189:9786
distributed.scheduler - INFO -  Bokeh UI at:  http://10.115.249.189:8787/status/
distributed.core - INFO - Connection from 10.112.2.3:50873 to Scheduler
distributed.scheduler - INFO - Register 10.112.2.3:59918
distributed.scheduler - INFO - Starting worker compute stream, 10.112.2.3:59918
distributed.core - INFO - Connection from 10.112.0.6:55149 to Scheduler
distributed.scheduler - INFO - Register 10.112.0.6:55103
distributed.scheduler - INFO - Starting worker compute stream, 10.112.0.6:55103
bokeh.command.subcommands.serve - INFO - Check for unused sessions every 50 milliseconds
bokeh.command.subcommands.serve - INFO - Unused sessions last for 1 milliseconds
bokeh.command.subcommands.serve - INFO - Starting Bokeh server on port 8787 with applications at paths ['/status', '/tasks']
distributed.core - INFO - Connection from 10.112.1.1:59452 to Scheduler
distributed.core - INFO - Connection from 10.112.1.1:59453 to Scheduler
distributed.core - INFO - Connection from 10.112.1.4:48952 to Scheduler
distributed.scheduler - INFO - Register 10.112.1.4:54760
distributed.scheduler - INFO - Starting worker compute stream, 10.112.1.4:54760
```

### Run commands

we can also execute arbitrary commands inside the running containers with
`kubectl exec`, for instance to open an interactive shell session for debugging
purposes:

```
$ kubectl exec -ti dask-scheduler-hebul bash
root@dscheduler-hebul:/work# ls -l examples/
total 56
-rw-r--r-- 1 basicuser root  1344 May 17 11:29 distributed_joblib_backend.py
-rw-r--r-- 1 basicuser root 33712 May 17 11:29 sklearn_parameter_search.ipynb
-rw-r--r-- 1 basicuser root 14407 May 17 11:29 sklearn_parameter_search_joblib.ipynb
```

where "dask-scheduler-hebul" is the specific pod name of the scheduler.

It is, of course, also possible to run shell commands directly in the Jupyter
notebook, or to use python's `subprocess` with dask's `Client.run` to
programmatically call commands on the worker containers.

### Alternate docker image

Each type of pod in dask-kubernetes currently is founded on the docker image
``mdurant/dask-kubernetes:latest``. The Dockerfile is included in this repo. Users
may wish to alter particularly the conda/pip installations in the middle of the work-flow.

There are two ways to apply changes made to a dask cluster:
- rebuild the docker image to the new specification, and post on dockerhub, changing
  the ``image:`` keys in the kubernetes .yaml files to point to it;
- set up a google image registry and build new images within your compute cluster.

To create a new password for the jupyter interface, execute the following in locally,
using a jupyter of similar version to the Dockerfile (currently 4.2)

```python
In [1]: from notebook.auth import passwd
In [2]: passwd()
Enter password:
Verify password:
Out[2]: '...'
```

and place the created output string into ``config/jupyter_notebook_config.py`` before
rebuildign the docker image.

### History

The original work was completed by @ogrisel.
