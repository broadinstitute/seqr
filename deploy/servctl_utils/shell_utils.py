import logging
import os
import subprocess # nosec
import sys
from io import StringIO

logger = logging.getLogger(__name__)

ALWAYS_IGNORE_WARNINGS = [
    'WARNING: the gcp auth plugin is deprecated',
    'Warning: storage.k8s.io/v1beta1 StorageClass is deprecated',
    'To learn more, consult https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke',
]


def run(command, errors_to_ignore=None, print_command=True, verbose=True, **kwargs):

    """Runs the given command in a shell.

    Args:
        command (string): the command to run
        errors_to_ignore (list): if the command's return code isn't ok, but its
            output contains one of the strings in this list, the bad return code will be ignored,
            and this function will return None. Otherwise, it raises a RuntimeException.
        print_command (bool): whether to print command before running
        verbose (bool): whether to print command output while command is running
    Return:
        string: command output (combined stdout and stderr), or if return_subprocess_obj=True the return 2-tuple: (output, subprocess Popen object)
    """
    full_env = dict(os.environ)  # copy external environment

    if print_command:
        logger.info("==> %(command)s" % locals())

    # pipe output to log
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=full_env, **kwargs) # nosec
    log_buffer = _get_command_output(p, verbose)
    p.wait()

    output = '\n'.join([line for line in log_buffer.getvalue().split('\n')
                        if all(ignore_str not in line for ignore_str in ALWAYS_IGNORE_WARNINGS)])

    if p.returncode != 0:
        should_ignore = False
        if errors_to_ignore:
            should_ignore = all(
                any([error_to_ignore in error for error_to_ignore in errors_to_ignore])
                for error in str(output.strip()).split('\n')
            )

        if should_ignore:
            return None
        else:
            raise RuntimeError(output)
    else:
        return output


def _get_command_output(p, verbose):
    line_buffer = StringIO()
    log_buffer = StringIO()
    previous_is_slash_r = False
    while True:
        out = p.stdout.read(1).decode('utf-8')
        if out == '' and p.poll() is not None:
            break
        if out != '':
            try:
                log_buffer.write(out)
                if verbose:
                    line_buffer.write(out)
                    if out.endswith('\r') or (out.endswith('\n') and previous_is_slash_r):
                        sys.stdout.write(line_buffer.getvalue())
                        sys.stdout.flush()
                        line_buffer = StringIO()
                        previous_is_slash_r = True
                    elif out.endswith('\n'):
                        line_content = line_buffer.getvalue().rstrip('\n')
                        if all(ignore_str not in line_content for ignore_str in ALWAYS_IGNORE_WARNINGS):
                            logger.info(line_content)
                        line_buffer = StringIO()
                        previous_is_slash_r = False
                    else:
                        previous_is_slash_r = False
            except UnicodeDecodeError:
                pass

    return log_buffer

