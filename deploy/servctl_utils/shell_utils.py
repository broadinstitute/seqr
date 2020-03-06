import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def run_in_background(command, print_command=True, env={}):
    """Runs the given command in a shell and returns without waiting for the command to finish.

    Args:
        command (string): the command to run
        print_command (bool): whether to print command before running
        env (dict): A custom environment in which to run
    Return:
        subprocess Popen object
    """
    full_env = dict(os.environ)  # copy external environment
    full_env.update({key: str(value) for key, value in env.items()})  # make sure all values are strings

    if print_command:
        logger.info("==> %(command)s" % locals())

    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=full_env, bufsize=1)

    return p


def wait_for(procs):
    """Takes a list of subprocess.Popen objects and doesn't return until all these processes have completed"""

    for proc in procs:
        proc.wait()
