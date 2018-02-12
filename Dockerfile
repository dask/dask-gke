FROM ubuntu:16.04
MAINTAINER Martin Durant <martin.durant@utoronto.ca>

RUN apt-get update -yqq && apt-get install -yqq bzip2 git wget graphviz && rm -rf /var/lib/apt/lists/*

# Configure environment
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN mkdir -p /work/bin

# Install Python 3 from miniconda
ADD https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh miniconda.sh
RUN bash miniconda.sh -b -p /work/miniconda && rm miniconda.sh

# keep conda in user dir, so can do conda install in notebook
ENV PATH="/work/bin:/work/miniconda/bin:$PATH"

# Install pydata stack
RUN conda config --set always_yes yes --set changeps1 no --set auto_update_conda no
RUN conda install notebook psutil numpy pandas scikit-learn statsmodels pip numba \
        scikit-image datashader holoviews nomkl matplotlib lz4 tornado
RUN conda install -c conda-forge fastparquet s3fs zict python-blosc cytoolz dask distributed dask-searchcv gcsfs \
 && conda clean -tipsy \
 && pip install git+https://github.com/dask/dask-glm.git --no-deps\
 && pip install graphviz

RUN conda install -c conda-forge nodejs
RUN conda install -c conda-forge jupyterlab jupyter_dashboards ipywidgets \
 && jupyter labextension install @jupyter-widgets/jupyterlab-manager \
 && jupyter nbextension enable jupyter_dashboards --py --sys-prefix \
 && jupyter nbextension enable widgetsnbextension --py --sys-prefix \
 && conda clean -tipsy

RUN conda install -c bokeh bokeh \
 && jupyter labextension install jupyterlab_bokeh \
 && conda clean -tipsy \
 && npm cache clean --force

# Optional: Install the master branch of distributed and dask
RUN pip install git+https://github.com/dask/dask --upgrade --no-deps \
 && pip install git+https://github.com/dask/distributed --upgrade --no-deps \
 && pip install git+https://github.com/dask/gcsfs --upgrade \
 && pip install git+https://github.com/pydata/xarray --upgrade \
 && pip install git+https://github.com/zarr-developers/zarr --upgrade

# Install Tini that necessary to properly run the notebook service in docker
# http://jupyter-notebook.readthedocs.org/en/latest/public_server.html#docker-cmd
ENV TINI_VERSION v0.9.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /usr/bin/tini
# for further interaction with kubernetes
ADD https://storage.googleapis.com/kubernetes-release/release/v1.5.4/bin/linux/amd64/kubectl /usr/sbin/kubectl
RUN chmod +x /usr/bin/tini && chmod 0500 /usr/sbin/kubectl

# Add local files at the end of the Dockerfile to limit cache busting
COPY config /work/config
COPY examples /work/examples
ENTRYPOINT ["/usr/bin/tini", "--"]

# Create a non-priviledge user that will run the client and workers
ENV BASICUSER basicuser
ENV BASICUSER_UID 1000
RUN useradd -m -d /work -s /bin/bash -N -u $BASICUSER_UID $BASICUSER \
 && chown $BASICUSER /work \
 && chown $BASICUSER:users -R /work

