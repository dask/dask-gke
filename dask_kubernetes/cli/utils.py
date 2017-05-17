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


def mem_bytes(m):
    """Translate java memory spec to bytes"""
    mult = {'Ki': 2 ** 10, 'Mi': 2 ** 20, 'Gi': 2 ** 30}
    for k, v in mult.items():
        if k in m:
            return v * int(m.replace(k, ''))
    return m


def get_conf(settings, args):
    """Produce configuration dictionary

    Starts with default settings, applies given YAML file, and overrides
    with any further arguments, in that order.

    Parameters
    ----------
    settings: str or None
        YAML file with some or all of the entries in defaults.yaml
    args: list of strings
        Override parameters like "jupyter.port=443"."""
    conf = yaml.load(open(defaults).read())
    if settings is not None:
        conf.update(yaml.load(open(settings).read()))
    for arg in args:
        key, value = arg.split('=')
        conf0 = conf
        for key_part in key.split('.')[:-1]:
            conf0 = conf[key_part]
        conf0[key.split('.')[-1]] = value
    # worker memory should be slightly less than container capacity
    factor = float(conf['workers']['mem_factor'])
    conf['workers']['memory_per_worker2'] = int(factor * mem_bytes(
        conf['workers']['memory_per_worker']))
    conf['workers']['cpus_per_worker2'] = ceil(
        conf['workers']['cpus_per_worker'])
    return conf


def render_templates(conf, par):
    """Render given config into kubernetes yaml files, in par directory

    Parameters
    ----------
    conf: dict
        Configuration dictionary, from get_conf()
    par: str
        Directory to write to
    """
    jenv = jinja2.Environment()
    for f in os.listdir(template_dir):
        fn = os.path.join(template_dir, f)
        templ = jenv.from_string(open(fn).read())
        out = os.path.join(par, f)
        with open(out, 'w') as f:
            f.write(templ.render(conf))
