
#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **4 CPUs**, **50 Gb disk space**  

 - *Software:* 
   - [docker](https://docs.docker.com/install/)
     - under Preferences > Resources > Advanced set the memory limit to at least 12 Gb  
   - [docker-compose](https://docs.docker.com/compose/install/)       
   - [gcloud](https://cloud.google.com/sdk/install)


#### Starting seqr

```
SEQR_DIR=$(pwd)

wget https://raw.githubusercontent.com/macarthur-lab/seqr/local_hail_v02/docker-compose.yml

docker-compose up -d seqr   # start up the seqr docker image in the background after also starting other components it depends on (postgres, redis, elasticsearch, phenotips). This may take 10+ minutes.
docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 

docker-compose exec seqr python manage.py createsuperuser  # create a seqr Admin user 

open http://localhost     # open the seqr landing page in your browser. Log in to seqr using the email and password from the previous step
```
   
#### Annotating and loading a VCF callset using a Google Dataproc cluster

TODO 
   
#### Annotating and loading a VCF callset on-prem

Annotating a callset with VEP and reference data can be very slow - as slow as several variants / sec per CPU.

To do this, first download VEP reference data:
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
3. Enter the elasticsearch index name (set via the `--es-index` arg at loading time. The pipeline also prints this out when it completes). Submit the form.


#### Enable read viewing in the browser (optional): 

To make .bam/.cram files viewable in the browser through igv.js, see **[ReadViz Setup Instructions](deploy/READVIZ_SETUP.md)**      
