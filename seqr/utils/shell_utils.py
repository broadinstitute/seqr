import logging
import os
import StringIO
import subprocess
import threading

logger = logging.getLogger()


class _LogPipe(threading.Thread):
    """Based on: https://codereview.stackexchange.com/questions/6567/redirecting-subprocesses-output-stdout-and-stderr-to-the-logging-module """

    def __init__(self, log_level=logging.INFO, verbose=True, cache_output=False):

        """Thread that reads data from a pipe and forwards it to logging.log"""
        threading.Thread.__init__(self)

        self.log_level = log_level
        self.verbose = verbose
        self.cache_output = cache_output
        if cache_output:
            self.log_output_buffer = StringIO.StringIO()

        self.fd_read, self.fd_write = os.pipe()
        self.pipe_reader = os.fdopen(self.fd_read)

        self.start()

    def fileno(self):
        """Return the write file descriptor of the pipe"""

        return self.fd_write

    def run(self):
        """Run the thread, forwarding pipe data to logging"""

        for line in iter(self.pipe_reader.readline, ''):
            self.log_output_buffer.write(line)
            if self.verbose:
                logging.log(self.log_level, line.strip('\n'))

        self.pipe_reader.close()

    def close(self):
        """Close the write end of the pipe."""
        os.close(self.fd_write)

    def get_log(self):
        if not self.cache_output:
            raise Exception("get_log() can be called if cache_output=True is passed to the constructor")

        return self.log_output_buffer.getvalue()


def run_shell_command(command, is_interactive=False, wait_and_return_log_output=False, verbose=True, env={}):
    """Runs the given command in a shell.

    Args:
        command (string): the command to run
        is_interactive (bool): Whether this command expects interactive input from the user
        wait (bool): Whether to wait for the command to finish before returning
        verbose (bool): whether to print command to log
        env (dict): A custom environment in which to run
    Return:
        subprocess Popen object
    """
    full_env = dict(os.environ)  # copy external environment
    full_env.update(env)

    full_env.update({ key: str(value) for key, value in full_env.items() })  # make sure all values are strings

    if verbose:
        with_env = ""  # ("with env: " + ", ".join("%s=%s" % (key, value) for key, value in full_env.items())) if full_env else ""
        logger.info("Running: '%(command)s' %(with_env)s" % locals())

    if not is_interactive:
        # pipe output to log
        stdout_pipe = _LogPipe(logging.INFO, verbose=verbose, cache_output=wait_and_return_log_output)
        stderr_pipe = _LogPipe(logging.ERROR, verbose=verbose, cache_output=wait_and_return_log_output)
        p = subprocess.Popen(command, shell=True, stdout=stdout_pipe, stderr=stderr_pipe, env=full_env)
        stdout_pipe.close()
        stderr_pipe.close()
    else:
        p = subprocess.Popen(command, shell=True, env=full_env)

    if wait_and_return_log_output:
        p.wait()
        return stdout_pipe.get_log(), stderr_pipe.get_log()

    return p


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
