import logging
import os

from seqr.utils.shell_utils import run_shell_command
from deploy.kubernetes.utils.seqrctl_utils import _get_pod_name, check_kubernetes_context

logger = logging.getLogger(__name__)


def load_project(deployment_label, project_id="1kg", genome_version="37", vcf=None, ped=None):
    """Load example project

    Args:
        project_id (string): project id
        genome_version (string): reference genome version - either "37" or "38"
        vcf (string): VCF path
        ped (string): PED path
    """

    check_kubernetes_context(deployment_label)

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    if not project_id:
        raise ValueError("project_id not specified")
    if not vcf:
        raise ValueError("vcf not specified")
    if not ped:
        raise ValueError("ped not specified")

    vcf_filename = os.path.basename(vcf)
    ped_filename = os.path.basename(ped)

    run_shell_command("kubectl exec %(pod_name)s -- wget -N %(vcf)s" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- wget -N %(ped)s" % locals()).wait()

    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_project '%(project_id)s' '%(project_id)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_individuals_to_project '%(project_id)s' --ped '%(ped_filename)s'" % locals()).wait()

    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_vcf_to_project --clear '%(project_id)s' '%(vcf_filename)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_project_to_phenotips '%(project_id)s' '%(project_id)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_individuals_to_phenotips '%(project_id)s' --ped '%(ped_filename)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py generate_pedigree_images -f '%(project_id)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py add_default_tags '%(project_id)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_project '%(project_id)s'" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_project_datastore '%(project_id)s'" % locals()).wait()


def load_example_project(deployment_label, genome_version="37"):
    """Load example project

    Args:
        genome_version (string): reference genome version - either "37" or "38"
    """

    check_kubernetes_context(deployment_label)

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    if genome_version == "37":
        vcf_filename = "1kg.vep.vcf.gz"
    elif genome_version == "38":
        vcf_filename = "1kg.liftover.GRCh38.vep.vcf.gz"
    else:
        raise ValueError("Unexpected genome_version: %s" % str(genome_version))

    project_id = "1kg"
    vcf = "https://storage.googleapis.com/seqr-public/test-projects/1kg-exomes/%(vcf_filename)s" % locals()
    ped = "https://storage.googleapis.com/seqr-public/test-projects/1kg-exomes/1kg.ped"

    load_project(deployment_label, project_id=project_id, genome_version=genome_version, vcf=vcf, ped=ped)


def load_reference_data(deployment_label, genome_version="37"):
    """Load reference data

    Args:
        genome_version (string): reference genome version - either "37" or "38"
    """

    check_kubernetes_context(deployment_label)

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    run_shell_command("kubectl exec %(pod_name)s -- mkdir -p /data/reference_data/" % locals())
    run_shell_command("kubectl exec %(pod_name)s -- wget -N https://storage.googleapis.com/seqr-public/reference-data/seqr-resource-bundle.GRCh%(genome_version)s.tar.gz -P /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- tar -xzf /data/reference_data/seqr-resource-bundle.GRCh%(genome_version)s.tar.gz --directory /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_resources" % locals()).wait()

    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py update_gencode /data/reference_data/gencode.v19.annotation.gtf.gz" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py update_human_phenotype_ontology" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py update_omim" % locals()).wait()

    run_shell_command("kubectl exec %(pod_name)s -- /usr/local/bin/restart_server.sh" % locals()).wait()


def load_allele_frequencies(deployment_label, genome_version="37"):
    """Load ExAC and 1kg allele frequency datasets. These are larger and take longer to load than other reference data

    Args:
        genome_version (string): reference genome version - either "37" or "38"
    """

    check_kubernetes_context(deployment_label)

    pod_name = _get_pod_name('seqr')
    if not pod_name:
        raise ValueError("No 'seqr' pods found. Is the kubectl environment configured in this terminal? and has this type of pod been deployed?" % locals())

    run_shell_command("kubectl exec %(pod_name)s -- wget -N http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz -P /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- wget -N http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz -P /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_reference" % locals()).wait()
