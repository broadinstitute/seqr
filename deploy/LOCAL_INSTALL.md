
#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **4 CPUs**, **50 Gb disk space**  

 - *Software:* 
   - [docker](https://docs.docker.com/install/)
     - under Preferences > Resources > Advanced set the memory limit to at least 12 Gb  
   - [docker-compose](https://docs.docker.com/compose/install/)       
   - [gcloud](https://cloud.google.com/sdk/install)


#### Starting seqr

```
wget https://raw.githubusercontent.com/macarthur-lab/seqr/local_hail_v02/docker-compose.yml

docker-compose up -d seqr   # start up the seqr docker image in the background after also starting other components it depends on (postgres, redis, elasticsearch, phenotips). This may take 10+ minutes.
docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 

docker-compose exec seqr python manage.py createsuperuser  # create a seqr Admin user 

open http://localhost     # open the seqr landing page in your browser. Log in to seqr using the email and password from the previous step
```
   
   
#### Loading a VCF callset into elasticsearch - pre-requisites

Annotating a callset with VEP and reference data can be very slow - as slow as several variants / sec per CPU.
  
```
# download VEP reference data - TODO share reference data in non-requestor-pays buckets
mkdir -p ./data/vep_data/homo_sapiens
cd ./data/vep_data/homo_sapiens
gsutil -u $PROJECT cat gs://hail-us-vep/homo-sapiens/85_GRCh37.tar | tar xf - &   # for the VEP GRCh37 cache
gsutil -u $RPOJECT cat gs://hail-us-vep/homo-sapiens/95_GRCh38.tar | tar xf  - &   # for the VEP GRCh38 cache, run (can have both GRCh37 and GRCh38 at the same time)
```

Authenticate to gcloud to access reference data
```
gcloud auth application-default login  # authenticate to your gcloud account
```

#### Loading a VCF callset into elasticsearch:


```
mkdir ./data/input_vcfs/ 
cp your-callset.vcf.gz ./data/input_vcfs/   #
 
docker-compose up -d pipeline-runner            # start the pipeline-runner container 
docker-compose exec pipeline-runner /bin/bash   # open a shell inside the pipeline-runner container (analogous to ssh'ing into a remote machine)

# run a command like the one below inside the pipeline-runner container to load a dataset into elasticsearch
python3 -m seqr_loading SeqrMTToESTask --local-scheduler \
    --reference-ht-path gs://seqr-reference-data/GRCh37/all_reference_data/combined_reference_data_grch37.ht \
    --clinvar-ht-path gs://seqr-reference-data/GRCh37/clinvar/clinvar.GRCh37.ht \
    --vep-config-json-path /vep85-GRCh37-loftee-gcloud.json \
    --es-host elasticsearch \
    --es-index-min-num-shards 3 \
    --sample-type WES \
    --es-index 1kg \
    --genome-version 37 \
    --source-paths gs://seqr-datasets/GRCh37/1kg/1kg.vcf.gz \
    --dest-path gs://seqr-datasets/GRCh37/1kg/1kg.mt \
 
```

After the dataset is loaded into elasticsearch, it can be added to the project:

1. Go to the project page
2. Click on Edit Datasets
3. Enter the index name that the pipeline printed out when it completed, and submit the form.

After this you can click "Variant Search" for each family, or "Gene Search" to search across families.


#### Enable read viewing in the browser (optional): 

To make .bam/.cram files viewable in the browser through igv.js, see **[ReadViz Setup Instructions](deploy/READVIZ_SETUP.md)**      
