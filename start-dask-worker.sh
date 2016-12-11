#!/bin/bash
NCPUS=`python -c "import multiprocessing as mp; print(mp.cpu_count())"`
echo "Detected $NCPUS cpus"
# Alternatively start one python process per CPU
# exec su $BASICUSER -c "env PATH=$PATH dask-worker dask-scheduler:8786 --nthreads 1 --nprocs $NCPUS $*"
exec su $BASICUSER -c "env PATH=$PATH dask-worker dask-scheduler:8786 $*"
