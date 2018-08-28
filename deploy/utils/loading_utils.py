import logging
import os

from deploy.utils.kubectl_utils import get_pod_name, run_in_pod
from deploy.utils.servctl_utils import check_kubernetes_context

logger = logging.getLogger(__name__)


def load_new_project(deployment_target, project_name, genome_version, sample_type, dataset_type, vcf, ped):
    """Load example project

    Args:
        deployment_target (string):
        project_id (string): project id
        genome_version (string): reference genome version - either "37" or "38"
        sample_type (string): "WES", "WGS", etc.
        dataset_type (string): "VARIANTS", "SV", etc.
        vcf (string): VCF path
        ped (string): PED path
    """

    check_kubernetes_context(deployment_target)

    pod_name = get_pod_name('seqr', deployment_target=deployment_target)
    if not pod_name:
        raise ValueError("No 'pipeline-runner' or 'seqr' pods found. Is the kubectl environment configured in this terminal? and have either of these pods been deployed?" % locals())

    if not project_name:
        raise ValueError("project_id not specified")
    if not vcf:
        raise ValueError("vcf not specified")
    if not ped:
        raise ValueError("ped not specified")

    if ped.startswith("http"):
        run_in_pod(pod_name, "wget -N %(ped)s" % locals())
        ped = os.path.basename(ped)
    elif ped.startswith("gs:"):
        run_in_pod(pod_name, "gsutil cp %(ped)s ." % locals())
        ped = os.path.basename(ped)

    # TODO call APIs instead?
    run_in_pod(pod_name, "python2.7 -u -m manage create_project -p '%(ped)s' '%(project_name)s'" % locals(), verbose=True)

    pod_name = get_pod_name('pipeline-runner', deployment_target=deployment_target)
    if vcf.startswith("http"):
        run_in_pod(pod_name, "wget -N %(vcf)s" % locals())
        vcf = os.path.basename(vcf)

    run_in_pod(pod_name, """/hail-elasticsearch-pipelines/run_hail_locally.sh \
        hail_scripts/v01/load_dataset_to_es.py \
            --genome-version %(genome_version)s \
            --project-guid %(project_id)s \
            --sample-type %(sample_type)s \
            --dataset-type %(dataset_type)s \
            --skip-validation \
            --exclude-hgmd \
            --vep-block-size 10 \
            --es-block-size 10 \
            --num-shards 1 \
            --max-samples-per-index 99 \
            %(vcf)s
    """ % locals(), verbose=True)


def load_example_project(deployment_target, genome_version="37"):
    """Load example project

    Args:
        deployment_target (string):
        genome_version (string): reference genome version - either "37" or "38"
    """

    check_kubernetes_context(deployment_target)

    if genome_version == "37":
        vcf_filename = "1kg.vep.vcf.gz"
    elif genome_version == "38":
        vcf_filename = "1kg.liftover.GRCh38.vep.vcf.gz"
    else:
        raise ValueError("Unexpected genome_version: %s" % (genome_version,))

    project_name = "1kg"
    vcf = "https://storage.googleapis.com/seqr-reference-data/test-projects/%(vcf_filename)s" % locals()
    ped = "https://storage.googleapis.com/seqr-reference-data/test-projects/1kg.ped"

    load_new_project(
        deployment_target,
        project_name=project_name,
        genome_version=genome_version,
        sample_type="WES",
        dataset_type="VARIANTS",
        vcf=vcf,
        ped=ped)


def update_reference_data(deployment_target):
    """Load reference data

    Args:
        deployment_target (string):
    """

    check_kubernetes_context(deployment_target)

    pod_name = get_pod_name('seqr', deployment_target=deployment_target)
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and have either of these pods been deployed?" % locals())

    run_in_pod(pod_name, "python2.7 -u manage.py update_all_reference_data --omim-key '$OMIM_KEY'" % locals(), verbose=True, print_command=True)

    run_in_pod(pod_name, "mkdir -p /seqr/data/reference_data")
    run_in_pod(pod_name, "wget https://storage.googleapis.com/seqr-reference-data/seqr-resource-bundle.tar.gz -O /seqr/data/reference_data/seqr-resource-bundle.tar.gz")
    run_in_pod(pod_name, "tar xzf /seqr/data/reference_data/seqr-resource-bundle.tar.gz -C /seqr/data/reference_data", verbose=True)
    run_in_pod(pod_name, "rm /seqr/data/reference_data/seqr-resource-bundle.tar.gz")

    run_in_pod(pod_name, "git checkout dev")
    run_in_pod(pod_name, "git pull")
    run_in_pod(pod_name, "python -u manage.py load_resources", verbose=True)


def create_user(deployment_target, email=None, password=None):
    """Creates a seqr superuser

    Args:
        deployment_target (string):
        email (string): if provided, user will be created non-interactively
        password (string): if provided, user will be created non-interactively
    """
    check_kubernetes_context(deployment_target)

    if not email:
        run_in_pod("seqr", "python -u manage.py createsuperuser" % locals(), is_interactive=True)
    else:
        logger.info("Creating user %(email)s" % locals())
        run_in_pod("seqr",
            """echo "from django.contrib.auth.models import User; User.objects.create_superuser('%(email)s', '%(email)s', '%(password)s')" \| python manage.py shell""" % locals(),
            print_command=False,
            errors_to_ignore=["already exists"])
