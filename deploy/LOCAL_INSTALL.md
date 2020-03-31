
#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **4 CPUs**, **50 Gb disk space**  

 - *Software:* 
   - [docker](https://docs.docker.com/install/)
     - under Preferences > Resources > Advanced set the memory limit to at least 12 Gb  
   - [docker-compose](https://docs.docker.com/compose/install/)       
   - [gcloud](https://cloud.google.com/sdk/install)


#### Starting seqr

The steps below describe how to create a new empty seqr instance with a single Admin user account.

```
SEQR_DIR=$(pwd)

wget https://raw.githubusercontent.com/macarthur-lab/seqr/local_hail_v02/docker-compose.yml

docker-compose up -d seqr   # start up the seqr docker image in the background after also starting other components it depends on (postgres, redis, elasticsearch, phenotips). This may take 10+ minutes.
docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 

docker-compose exec seqr python manage.py createsuperuser  # create a seqr Admin user 

open http://localhost     # open the seqr landing page in your browser. Log in to seqr using the email and password from the previous step
```
   
#### Annotating and loading VCF callsets - option #1: annotate on a Google Dataproc cluster, then load in to an on-prem seqr instance 

Google Dataproc makes it easy to parallelize annotation across many machines.
The steps below describe how to annotate a callset and then load it into your on-prem elasticsearch instance.

1. authenticate into your google account
   ```
   gcloud auth application-default login  
   ```
1. upload your .vcf.gz callset to a google bucket - for example `gs://your-bucket/data/GRCh37/your-callset.vcf.gz`

1. start a pipeline-runner container which has the necessary tools and environment pre-installed.
   ```
   SEQR_DIR=$(pwd)
   
   wget https://raw.githubusercontent.com/macarthur-lab/seqr/local_hail_v02/docker-compose.yml
   
   docker-compose up -d pipeline-runner            # start the pipeline-runner container 
   docker-compose exec pipeline-runner /bin/bash   # open a shell inside the pipeline-runner container (analogous to ssh'ing into a remote machine)
   ```
1. in the pipeline-runner shell, use the hailctl utility to start a Dataproc cluster (adjust the arguments as needed, particularly `--vep GRCh38` vs. `GRCh37`), submit the annotation job, and when that's done, load the annotated dataset into your local elasticsearch instance.
   ```
   cd /hail-elasticsearch-pipelines/luigi_pipeline
   
   # create dataproc cluster
   hailctl dataproc start \
       --pkgs luigi,google-api-python-client \
       --vep GRCh38 \
       --max-idle 30m \
       --num-workers 2 \
       --num-preemptible-workers 12 \
       seqr-loading-cluster

   # submit annotation job to dataproc cluster
   hailctl dataproc submit seqr-loading-cluster \
       seqr_loading.py --pyfiles "lib,../hail_scripts" \
       SeqrVCFToMTTask --local-scheduler \
            --source-paths gs://your-bucket/data/GRCh38/your-callset.vcf.gz \
            --dest-path gs://your-bucket/data/GRCh37/your-callset.mt \
            --genome-version 38 \
            --sample-type WES \
            --reference-ht-path  gs://seqr-reference-data/GRCh38/all_reference_data/combined_reference_data_grch38.ht \
            --clinvar-ht-path gs://seqr-reference-data/GRCh38/clinvar/clinvar.GRCh38.ht
   
   gcloud dataproc jobs list    # run this to get the dataproc job id
   gcloud dataproc jobs wait ce9fcc69a5034522b3ea2cb8e83c444d   # view jobs logs and wait for the job to complete
   
   # load the annotated dataset into your local elasticsearch instance
   python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
        --dest-path gs://your-bucket/data/GRCh37/your-callset.mt \
        --es-host elasticsearch  \
        --es-index your-callset-name
   ``` 

   
#### #### Annotating and loading VCF callsets - option #2: annotate and load on-prem

Annotating a callset with VEP and reference data can be very slow - as slow as several variants / sec per CPU, so although it is possible to run the pipeline on a single machine, it is recommended to use multiple machines.

To annotate a callset on-prem, first download VEP reference data:
```
# authenticate to your gcloud account so you can download public reference data
gcloud auth application-default login  

# download VEP reference data
mkdir -p ${SEQR_DIR}/data/vep_data/homo_sapiens
cd ${SEQR_DIR}/data/vep_data
curl -L http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/homo_sapiens_vep_99_GRCh37.tar.gz | tar xzf - &   # for the VEP GRCh37 cache
curl -L http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/homo_sapiens_vep_99_GRCh38.tar.gz | tar xzf - &   # for the VEP GRCh38 cache (can have both the GRCh37 and GRCh38 caches at the same time)

#  - TODO share reference data in non-requestor-pays buckets
mkdir -p ${SEQR_DIR}/data/vep_data/loftee_data/GRCh37/
cd ${SEQR_DIR}/data/vep_data/loftee_data/GRCh37/
gsutil -u your-gcloud-project-name cat gs://hail-us-vep/loftee-beta/GRCh37.tar  | tar xf  - & 
```

Then run the following commands to annotate your callset and load it into elasticsearch:

```
# authenticate to your gcloud account so you can download public reference data
gcloud auth application-default login  

# if your data is local, create a directory for your vcf files. docker-compose will mount this directory into the pipeline-runner container.
mkdir ./data/input_vcfs/ 
cp your-callset.vcf.gz ./data/input_vcfs/       # vcfs should be bgzip'ed
 
docker-compose up -d pipeline-runner            # start the pipeline-runner container 
docker-compose exec pipeline-runner /bin/bash   # open a shell inside the pipeline-runner container (analogous to ssh'ing into a remote machine)

# for GRCh38 callsets, run a command like the one below inside the pipeline-runner container to annotate and load your dataset into elasticsearch
python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
    --reference-ht-path gs://seqr-reference-data/GRCh38/all_reference_data/combined_reference_data_grch38.ht \
    --clinvar-ht-path gs://seqr-reference-data/GRCh38/clinvar/clinvar.GRCh38.ht \
    --vep-config-json-path /vep85-GRCh38-loftee-gcloud.json \
    --es-host elasticsearch \
    --es-index-min-num-shards 3 \
    --sample-type WES \
    --es-index your-dataset-name \
    --genome-version 38 \
    --source-paths gs://your-bucket/GRCh38/your-callset.vcf.gz \   # this can also be a path inside /input_vcfs/
    --dest-path gs://your-bucket/GRCh38/your-callset.mt      # this can be a local or gs:// path where you have write access

# for GRCh37 callsets, run a command like the one below inside the pipeline-runner container to annotate and load your dataset into elasticsearch
python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
    --reference-ht-path gs://seqr-reference-data/GRCh37/all_reference_data/combined_reference_data_grch37.ht \
    --clinvar-ht-path gs://seqr-reference-data/GRCh37/clinvar/clinvar.GRCh37.ht \
    --vep-config-json-path /vep85-GRCh37-loftee-gcloud.json \
    --es-host elasticsearch \
    --es-index-min-num-shards 3 \
    --sample-type WES \
    --es-index your-dataset-name \
    --genome-version 37 \
    --source-paths gs://your-bucket/GRCh37/your-callset.vcf.gz \   # this can also be a path inside /input_vcfs/
    --dest-path gs://your-bucket/GRCh37/your-callset.mt      # this can be a local or gs:// path where you have write access

```


#### Adding a loaded dataset to a seqr project.

After the dataset is loaded into elasticsearch, it can be added to your seqr project with these steps:

1. Go to the project page
2. Click on Edit Datasets
3. Enter the elasticsearch index name (set via the `--es-index` arg at loading time), and submit the form.


#### Enable read viewing in the browser (optional): 

To make .bam/.cram files viewable in the browser through igv.js, see **[ReadViz Setup Instructions](deploy/READVIZ_SETUP.md)**      
