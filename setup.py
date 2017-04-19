#!/usr/bin/env python

from io import open
import re
from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

setup(name="dask-kubernetes",
      version="0.0.1",
      description="Dask Kubernetes",
      url="https://github.com/martindurant/dask-kubernetes",
      author="Joseph Crail",
      keywords='kubernetes',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      packages=find_packages(exclude=['tests']),
      install_requires=[
          'click'
      ],
      long_description=readme,
      entry_points="""
        [console_scripts]
        dask-kubernetes=dask_kubernetes.cli.main:start
      """)
