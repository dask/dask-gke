#!/usr/bin/env bash
jupyter notebook --config=/work/config/jupyter_notebook_config.py /work &
jupyter lab --port=8889 --config=/work/config/jupyter_notebook_config.py /work &
wait