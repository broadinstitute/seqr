import logging
import os

from seqr.utils.shell_utils import run_shell_command

logger = logging.getLogger(__name__)


class LocalHailRunner:

    def run_hail(self, script_path, *script_args):
        """Runs the hail script locally."""

        if not os.path.isfile(script_path):
            raise ValueError("Script file not found: %(script_path)s" % locals())

        script_args_string = " ".join(script_args)
        run_shell_command("python %(script_path)s -- %(script_args_string)s" % locals()).wait()

    def init_runner(self, *args, **kwargs):
        pass

    def delete_runner(self, *args, **kwargs):
        pass
