# some tasks are
import os
import logging
import subprocess
from datetime import datetime

import google.cloud.logging

from django.conf import settings
from django.conf.urls import url
from django.http import HttpResponse

# configure logging
client = google.cloud.logging.Client()
client.get_default_handler()
client.setup_logging()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

settings.configure(
    DEBUG=False,
    ALLOWED_HOSTS="*",
    ROOT_URLCONF=__name__,
    MIDDLEWARE_CLASSES=(
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ),
)

# ADD new modes here
MODES = {
    "update_human_phenotype_ontology": [],
    "import_all_panels": ["https://panelapp.agha.umccr.org/api/v1", "--label=AU"],
}


def index(request):
    start = datetime.now()
    try:
        mode = request.GET.get("mode")
        if mode not in MODES:
            return HttpResponse(f"Unrecognised mode: {mode}", status=400)

        logger.info(f'Running "{mode}"')
        command = ["python", "manage.py", mode, *MODES[mode]]
        process = subprocess.run(command, capture_output=True)
        seconds = (datetime.now() - start).total_seconds()

        if process.returncode == 0:
            logger.info(f"Success: {mode} ({seconds}s)")
            return HttpResponse(
                f"Completed ({seconds}s). STDERR: {process.stderr}. STDOUT: {process.stdout}",
                status=200,
            )

        logger.error(f"Failed {mode} ({seconds}s)")
        logger.warning(process.stdout)
        logger.error(process.stderr)
        return HttpResponse(
            f"Failed ({seconds}s). STDERR: {process.stderr}. STDOUT: {process.stdout}",
            status=500,
        )
    except Exception as e:
        seconds = (datetime.now() - start).total_seconds()

        logger.error(f"Globally caught exception after {seconds}s: {type(e)}, {e}")
        return HttpResponse("Failed, " + str(e), status=500)


urlpatterns = (url(r"^$", index),)


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    port = os.getenv("PORT", "5000")
    arguments = ["update_reference_server.py", "runserver", f"0.0.0.0:{port}"]
    execute_from_command_line(arguments)
