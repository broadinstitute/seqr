import logging
import os

from utils.shell_utils import run_shell_command
from utils.other_utils import retrieve_settings, check_kubernetes_context, lookup_json_path
from utils.seqrctl_utils import _get_pod_name

logger = logging.getLogger()


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


def _init_dataproc_cluster(settings, genome_version="37"):
    """Create a data-proc cluster.

    Args:
        settings (dict): global deployment settings
        genome_version (string): "37" or "38"
    """

    # TODO come up with a way to run hail locally

    GCLOUD_ZONE = settings['GCLOUD_ZONE']
    GCLOUD_PROJECT = settings['GCLOUD_PROJECT']

    # gs://hail-common/vep/vep/GRCh%(genome_version)s/vep85-GRCh%(genome_version)s-init.sh
    run_shell_command("""
    gcloud dataproc clusters create seqr-backend-export-cluster  \
        --zone %(GCLOUD_ZONE)s \
        --master-machine-type n1-standard-8 \
        --master-boot-disk-size 100 \
        --num-workers 2 \
        --worker-machine-type n1-standard-8 \
        --worker-boot-disk-size 100 \
        --num-preemptible-workers 2 \
        --image-version 1.1 \
        --project %(GCLOUD_PROJECT)s \
        --initialization-actions "gs://hail-common/hail-init.sh"
    """ % locals()).wait()


def _submit_to_hail(settings, script_path, node_name, vds_path):
    """
    """
    run_shell_command("""
    gcloud --project seqr-project dataproc jobs submit pyspark %(script_path)s \
           --cluster seqr-backend-export-cluster \
           --files=gs://seqr-hail/hail/hail-all-spark.jar \
           --py-files=gs://seqr-hail/hail/hail-python.zip \
           --properties=spark.driver.extraClassPath=./hail-all-spark.jar,spark.executor.extraClassPath=./hail-all-spark.jar \
           -- %(node_name)s %(vds_path)s
    """ % locals()).wait()


def load_project_solr(deployment_label, project_id="1kg", genome_version="37", vds_path="gs://seqr-hail/annotated/Cohen.1kpart.vds"):
    """Export VDS to solr

    Args:
        deployment_label (string): "local", "gcloud-dev", or "gcloud-prod"
        project_id (string): project id
        genome_version (string): reference genome version - either "37" or "38"
        vcf (string): VCF path
    """

    check_kubernetes_context(deployment_label)

    settings = retrieve_settings(deployment_label)

    _init_dataproc_cluster(settings, genome_version=genome_version)

    pod_name = lookup_json_path("pods", labels={'name': 'solr'}, json_path=".items[0].metadata.name")

    run_shell_command("kubectl exec %(pod_name)s -- su -c '/usr/local/solr-6.4.2/bin/solr delete -c seqr_noref' solr || true" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- su -c '/usr/local/solr-6.4.2/bin/solr create_collection -c seqr_noref' solr || true" % locals()).wait()

    script_path = "scripts/loading/export_to_solr.py"
    node_name = lookup_json_path("pods", labels={'name': 'solr'}, json_path=".items[0].spec.nodeName")

    _submit_to_hail(settings, script_path, node_name, vds_path)

    run_shell_command("kubectl exec -i %(pod_name)s -- /bin/bash -c \"curl 'http://localhost:30002/solr/seqr_noref/select?indent=on&q=*:*&wt=json'\"" % locals()).wait()


def load_project_cassandra(deployment_label, project_id="1kg", genome_version="37", vds_path="gs://seqr-hail/annotated/Cohen.1kpart.vds"):
    """Export VDS to cassandra

    Args:
        deployment_label (string): "local", "gcloud-dev", or "gcloud-prod"
        project_id (string): project id
        genome_version (string): reference genome version - either "37" or "38"
        vds_path (string): path of annotated VDS
    """

    check_kubernetes_context(deployment_label)

    settings = retrieve_settings(deployment_label)

    _init_dataproc_cluster(settings, genome_version=genome_version)

    pod_name = lookup_json_path("pods", labels={'name': 'cassandra'}, json_path=".items[0].metadata.name")

    run_shell_command("""
    kubectl exec -i %(pod_name)s -- cqlsh <<EOF
        DROP KEYSPACE IF EXISTS seqr;
        CREATE KEYSPACE seqr WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}  AND durable_writes = true;

        CREATE TABLE seqr.seqr (chrom text, start int, ref text, alt text, dataset_5fid text, PRIMARY KEY (chrom, start, ref, alt, dataset_5fid));
    EOF
    """ % locals()).wait()

    script_path = "scripts/loading/export_to_cass.py"
    node_name = lookup_json_path("pods", labels={'name': 'cassandra'}, json_path=".items[0].spec.nodeName")

    _submit_to_hail(settings, script_path, node_name, vds_path)

    run_shell_command("""
    kubectl exec -i %(pod_name)s -- cqlsh <<EOF
        select count(*) from seqr.seqr;
    EOF
    """ % locals()).wait()


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
    run_shell_command("kubectl exec %(pod_name)s -- wget -N https://storage.googleapis.com/seqr-public/reference-data/seqr-resource-bundle.tar.gz -P /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- tar -xzf /data/reference_data/seqr-resource-bundle.tar.gz --directory /data/reference_data/" % locals()).wait()
    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py load_resources" % locals()).wait()

    run_shell_command("kubectl exec %(pod_name)s -- python2.7 -u manage.py update_gencode" % locals()).wait()
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
