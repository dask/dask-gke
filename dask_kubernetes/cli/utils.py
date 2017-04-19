import functools
import subprocess
import sys

import click


def required_commands(*commands):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            """
            Fails if any required command is not available
            """
            failed = False
            for command in commands:
                try:
                    # Unix-specific command lookup
                    subprocess.check_output("which {}".format(command), shell=True)
                except subprocess.CalledProcessError:
                    click.echo("Required command does not exist: {}".format(command), err=True)
                    failed = True
            if failed:
                sys.exit(1)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def call(cmd):
    click.secho("executing: {}".format(cmd), fg='green')
    subprocess.call(cmd, shell=True)


def check_output(cmd):
    click.secho("executing: {}".format(cmd), fg='green')
    return subprocess.check_output(cmd, shell=True).decode("utf-8")
