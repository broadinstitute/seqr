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

def run(command,
        ok_return_codes=(0,),
        errors_to_ignore=None,
        ignore_all_errors=False,
        print_command=True,
        verbose=True,
        env=None,
        is_interactive=False, **kwargs):

    """Runs the given command in a shell.

    Args:
        command (string): the command to run
        ok_return_codes (list): list of returncodes that indicate the command succeeded
        errors_to_ignore (list): if the command's return code isn't in ok_return_codes, but its
            output contains one of the strings in this list, the bad return code will be ignored,
            and this function will return None. Otherwise, it raises a RuntimeException.
        ignore_all_errors (bool): if True, all non-zero return codes will be ignored.
        print_command (bool): whether to print command before running
        verbose (bool): whether to print command output while command is running
        wait (bool): Whether to wait for the command to finish before returning
        env (dict): A custom environment in which to run
    Return:
        string: command output (combined stdout and stderr), or if return_subprocess_obj=True the return 2-tuple: (output, subprocess Popen object)
    """
    full_env = dict(os.environ)  # copy external environment
    if env:
        full_env.update({key: str(value) for key, value in env.items()})  # make sure all values are strings

    if print_command:
        logger.info("==> %(command)s" % locals())

    if is_interactive:
        p = subprocess.Popen(command, shell=True, env=full_env) # nosec
        p.wait()
        return None

    # pipe output to log
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=full_env, encoding='utf-8', **kwargs) # nosec
    line_buffer = StringIO()
    log_buffer = StringIO()
    previous_is_slash_r = False
    while True:
        out = p.stdout.read(1)
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
    p.wait()

    output = '\n'.join([line for line in log_buffer.getvalue().split('\n')
                        if all(ignore_str not in line for ignore_str in ALWAYS_IGNORE_WARNINGS)])

    if p.returncode not in ok_return_codes:
        should_ignore = False
        if ignore_all_errors:
            should_ignore = True
        elif errors_to_ignore:
            should_ignore = all(
                any([error_to_ignore in error for error_to_ignore in errors_to_ignore])
                for error in  str(output.strip()).split('\n')
            )

        if should_ignore:
            return None
        else:
            raise RuntimeError(output)
    else:
        return output

