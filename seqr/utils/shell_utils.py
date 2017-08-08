import logging
import os
import StringIO
import subprocess

logger = logging.getLogger(__name__)


def run_shell_command_async(command, print_command=True, env={}):
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


def run_shell_command(command, ok_return_codes=(0,), print_command=True, verbose=True, env={}, is_interactive=False):
    """Runs the given command in a shell.

    Args:
        command (string): the command to run
        ok_return_codes (list): list of returncodes that indicate the command succeeded
        print_command (bool): whether to print command before running
        verbose (bool): whether to print command output while command is running
        wait (bool): Whether to wait for the command to finish before returning
        env (dict): A custom environment in which to run
    Return:
        string: command output (combined stdout and stderr), or if return_subprocess_obj=True the return 2-tuple: (output, subprocess Popen object)
    """
    full_env = dict(os.environ)  # copy external environment
    full_env.update({key: str(value) for key, value in env.items()})  # make sure all values are strings

    if print_command:
        logger.info("==> %(command)s" % locals())

    if is_interactive:
        p = subprocess.Popen(command, shell=True, env=full_env)
        p.wait()
        return None

    # pipe output to log
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=full_env, bufsize=1)
    log_buffer = StringIO.StringIO()
    for line in iter(p.stdout.readline, ''):
        log_buffer.write(line)
        if verbose:
            logger.info(line.strip('\n'))
    #p.stdout.close()

    p.wait()

    output = log_buffer.getvalue()
    if p.returncode not in ok_return_codes:
        raise RuntimeError(output)

    return output

def try_running_shell_command(command, errors_to_ignore=None, verbose=False, is_interactive=False):
    """Try running the given command and return results.

    Args:
        command (string): shell command to run
        errors_to_ignore (list): if an error occurs and its error message contains one of the
            strings in this list, the error will be ignored, and this function will return None.
            Otherwise, the error is re-raised.
    """

    try:
        return run_shell_command(command, verbose=verbose, is_interactive=is_interactive)
    except RuntimeError as e:
        if not (errors_to_ignore and any([error_to_ignore in str(e) for error_to_ignore in errors_to_ignore])):
            raise

        return None


def wait_for(procs):
    """Takes a list of subprocess.Popen objects and doesn't return until all these processes have completed"""

    for proc in procs:
        proc.wait()


def ask_yes_no_question(question):
    """Prompt the user and return True or False depending on whether they replied 'Y' or 'n'

    Args:
        question (string): question to ask
    """
    while True:
        i = raw_input(str(question) + " [Y/n] ")

        if i and i.lower() == 'y':
            return True
        elif i and i.lower() == 'n':
            return False
