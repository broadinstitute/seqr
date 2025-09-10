## Starting and Updating *seqr*

Detailed instructions for how to install and update *seqr* may be found in the [seqr-helm](https://github.com/broadinstitute/seqr-helm) repository. 

### Configuring Authentication for seqr

#### Username/password basic auth
This is the default authentication mechanism for seqr. After seqr is running, you can run the following steps to create an inital superuser account. 
All other user accounts can then be added through normal application use.

```bash
# Get the name of the running seqr pod
kubectl get pod

kubectl exec -it seqr-POD-ID -- /bin/bash
./manage.py createsuperuser
```

#### Google OAuth2
Using Google OAuth2 for authentication requires setting up a Google Cloud project and configuring the seqr instance 
with the project's client ID and secret by setting the following environment variables in your [helm values overrides](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#valuesenvironment-overrides):
```yaml
  seqr:
    environment:
      - SOCIAL_AUTH_GOOGLE_OAUTH2_CLIENT_ID=your-client-id
      - SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-client-secret
```
Note that user accounts do NOT need to be associated with this Google Cloud 
project in order to have access to seqr. User's emails must explicitly be added to at least one seqr project for them to
gain any access to seqr, and any valid Gmail account can be used.

#### Azure OAuth2
Using Azure OAuth2 for authentication requires setting up an Azure tenant and configuring the seqr instance with the 
tenant and it's client ID and secret by setting the following environment variables in your [helm values overrides](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#valuesenvironment-overrides):
```yaml
  seqr:
    environment:
      - SOCIAL_AUTH_AZUREAD_V2_OAUTH2_CLIENT_ID=your-client-id
      - SOCIAL_AUTH_AZUREAD_V2_OAUTH2_SECRET=your-client-secret
      - SOCIAL_AUTH_AZUREAD_V2_OAUTH2_TENANT=your-tenant-id 
```
Note that user accounts must be directly associated with the Azure tenant in order to access seqr. Anyone with access
to the tenant will automatically have access to seqr, although they will only be able to view those projects that they 
have been added to.

## Enabling Clingen Allele Registration
- Turning on this feature will register your variants within the Clingen Allele Registry during VCF ingestion. The [Registry](https://reg.clinicalgenome.org/redmine/projects/registry/genboree_registry/landing) provides and maintains unique variant identifiers; enabling this feature will toggle several small features.
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

## Using the Load Data page to load VCF Callsets
### Option #1
#### Annotate and load on-prem
- Copy your vcf into the loading datasets directory on the node running your kubernetes cluster (`/var/seqr/seqr-loading-temp/`).  You should see your vcf present when listing files:
```
ls -h /var/seqr/seqr-loading-temp/
loading_pipeline_queue  test.vcf.gz
```
- Ensure Families and Individuals are created in the project(s) of interest.
- In the top header of *seqr*, click on the **Data Management** button.
- In the subheader, click on **Load Data**.
- Select your VCF from the dropdown and select the appropriate Sample Type (WES/WGS) and Genome Version (GRCh37/GRCh38) for your project.  The pipeline includes a sequence of validation steps to insure the validity of your VCF, but these may be skipped by enabling the **Skip Callset Validation** option.  We strongly recommend leaving validation enabled to ensure the quality of your analysis.
- Click through to the next page and select your project(s) from the **Projects to Load** dropdown, then click **Submit**.
- If you wish to check the status of the loading request, you can click through to the **Pipeline Status** tab to view the loading pipeline interface.
- Data should be loaded into the search backend automatically, usually within a few hours.

### Option #2
####  Annotate on and load on a Google Dataproc cluster.

Google Dataproc makes it easy to start a spark cluster which can be used to parallelize annotation across many machines.  This option is available if you are running the *seqr* application on either a Google Cloud Platform VM or GKE.

- Verify that the seqr pod has an associated service account.
```
kubectl exec seqr-POD-ID -c seqr -it -- bash
gcloud auth list
```
This service account must be permissioned to create and modify dataproc clusters, and read and write to the GCS buckets that will host your data.  We also recommend verifying that the Cloud API access scopes are permissioned for both IAM and Compute Engine access.  
- Create or add the following environment variables to your existing `helm` [override values file](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#valuesenvironment-overrides):
```yaml
pipeline-runner:
  environment:
    # Stores authoritative copies of your hail search data.
    # Objects should not expire from this bucket.
    HAIL_SEARCH_DATA_DIR: 'gs://...'
    # Bucket used as a scratch directory by HAIL during loading.
    # We recommend a <1 week expiration policy for this bucket.
    HAIL_TMP_DIR: 'gs://...'
    # Bucket used for caching and worker communcation by the pipeline.
    # We recommend a ~2 week expiration policy for this bucket.
    LOADING_DATASETS_DIR: 'gs://...'
    # Stores a copy of seqr's reference data hosted in your project's account.
    # Objects should not expire from this bucket.
    REFERENCE_DATASETS_DIR: 'gs://...'
    RUN_PIPELINE_ON_DATAPROC: '1'
    GCLOUD_PROJECT: 'your-gcp-project'
    GCLOUD_REGION: 'region-of-dataproc-cluster'
    GCLOUD_ZONE: 'zone-of-dataproc-cluster'
seqr:
  environment:
    # Bucket used for caching and worker communcation by the pipeline.
    # Must be identical to `LOADING_DATASETS_DIR` stored above.
    LOADING_DATASETS_DIR: 'gs://...'
```
- Install/Upgrade with the override values applied:
```
helm upgrade YOUR_INSTITUTION_NAME-seqr seqr-helm/seqr-platform -f my-values.yaml
```
- Follow the Option #1 Instructions to load data from the **Load Data** page.

## Loading RNASeq datasets

Currently, seqr has a preliminary integration for RNA data, which requires the use of publicly available 
pipelines run outside of the seqr platform. After these pipelines are run, the output must be annotated with metadata 
from seqr to ensure samples are properly associated with the correct seqr families. After calling is completed, it can
be added to seqr from the "Data Management" > "Rna Seq" page. You will need to provide the file path for the data and the 
data type. Note that the file path can either be a gs:// path to a google bucket or as a local file stored in the `/var/seqr` folder. 

The following data types are supported:

#### Gene Expression

seqr accepts normalized expression TPMs from STAR or RNAseqQC. TSV files should have the following columns:

- sample_id
- project
- gene_id
- TPM
- tissue

#### Expression Outliers

seqr accepts gene expression outliers from OUTRIDER.  TSV files should have the following columns:

- sampleID
- geneID
- pValue
- padjust
- zScore

#### IGV

Splice junctions (.junctions.bed.gz) and coverage (.bigWig) can be visualized in seqr using IGV.
See [ReadViz Setup](READVIZ_SETUP.md) for 
instructions on adding this data, as the process is identical for all IGV tracks. 
