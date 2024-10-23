## Starting and Updating *seqr*

Detailed instructions for how to install and update *seqr* may be found in the [seqr-helm](https://github.com/broadinstitute/seqr-helm) repository. 

## Configuring Authentication for *seqr*

See the instructions provided in [LOCAL_INSTALL.md](LOCAL_INSTALL.md#configuring-authentication-for-seqr).

## Enabling Clingen Allele Registration
- You will first need to [register](https://reg.clinicalgenome.org/cg-prof/new) and receive a login and password.
- Create a kubernetes secret called `pipeline-secrets` with your login and password embedded:
```bash
kubectl create secret generic pipeline-secrets \
  --from-literal=clingen_allele_registry_login='my-login'
  --from-literal=clingen_allele_registry_password='my-password'
```
- Add secret references in your [values overrides](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#valuesenvironment-overrides):
```yaml
pipeline-runner:
  additionalSecrets:
    - name: CLINGEN_ALLELE_REGISTRY_LOGIN
      valueFrom:
        secretKeyRef:
          name: pipeline-secrets
          key: clingen_allele_registry_login
    - name: CLINGEN_ALLELE_REGISTRY_PASSWORD
      valueFrom:
        secretKeyRef:
          name: pipeline-secrets
          key: clingen_allele_registry_password
```

## How to Use the Load Data Interface
- In the top header of *seqr*, click on the **Data Management** button.
- In the subheader, click on **Load Data**.
- Copy your vcf into the directory the loading datasets directory, `/var/seqr/seqr-loading-temp/`.  You should see something your vcf present:
```
ls -h /var/seqr/seqr-loading-temp/
loading_pipeline_queue  test.vcf.gz
```
- Type the name of the callset path into the *Callset File Path* text box (without the directory prefix), and select the appropriate Sample Type (WES/WGS) and Genome Version (GRCh37/GRCh38) for your project.  The pipeline includes a sequence of validation steps to insure the validity of your VCF, but these may be skipped by enabling the *Skip Callset Validation*option.  We strongly recommend leaving validation enabled to ensure the quality of your analysis.
- Click through to the next page and select your project from the *Projects to Load* dropdown, then click *Submit*.
- If you wish to check the status of the loading request, you can click through to the *Pipeline Status* tab to view the loading pipeline interface.

## Enable read viewing in the browser

To make .bam/.cram files viewable in the browser through igv.js, see [ReadViz Setup](READVIZ_SETUP.md).

## Loading RNASeq datasets

See the instructions provided in [LOCAL_INSTALL.md](LOCAL_INSTALL.md#configuring-authentication-for-seqr#loading-rnaseq-datasets).