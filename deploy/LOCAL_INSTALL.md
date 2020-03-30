
#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **4 CPUs**, **50 Gb disk space**  

 - *Software:* 
   - python2.7
   - [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
   - [docker](https://docs.docker.com/install/)
     - under Preferences > Resources > Advanced set the memory limit to at least 12 Gb  
   - [docker-compose](https://docs.docker.com/compose/install/)       
   - [gcloud](https://cloud.google.com/sdk/install)


#### Starting seqr:

```
git clone https://github.com/macarthur-lab/seqr.git   # clone the seqr repo
cd seqr
git checkout local_hail_v02   # switch to the local_hail_v02 branch
docker-compose up -d seqr   # start up the seqr docker image in the background after also starting other components it depends on (postgres, redis, elasticsearch, phenotips). This may take 10+ minutes.
docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 

docker-compose exec seqr python manage.py createsuperuser  # create a seqr Admin user 

open http://localhost     # open the seqr landing page in your browser. Log in to seqr using the email and password from the previous step
```
   
   
#### Loading data (not done testing this section):

```
gcloud auth application-default login  # authenticate to your gcloud account

cd seqr

mkdir -p vep_data/homo_sapiens
cd vep_data/homo_sapiens

# download VEP data - TODO share via non-requestor-pays buckets
gsutil -u $PROJECT cat gs://hail-us-vep/homo-sapiens/85_GRCh37.tar | tar xf - &
gsutil -u $RPOJECT cat gs://hail-us-vep/homo-sapiens/95_GRCh38.tar | tar xf  - & 

docker run -v $(pwd)/vep_data/:/vep_data/ -v ~/.config:/root/.config -it --network seqr_default gcr.io/seqr-project/pipeline-runner:gcloud-dev /bin/bash
   
# inside the pipeline-runner docker container:
~$ cd hail-elasticsearch-pipelines/luigi_pipeline/

# example command
~$ python3 seqr_loading.py SeqrMTToESTask --local-scheduler --source-paths gs://seqr-datasets/GRCh37/1kg/1kg.vcf.gz --dest-path gs://seqr-datasets/GRCh37/1kg/1kg.mt --genome-version 37 --reference-ht-path gs://seqr-reference-data/GRCh37/all_reference_data/combined_reference_data_grch37.ht --clinvar-ht-path gs://seqr-reference-data/GRCh37/clinvar/clinvar.GRCh37.ht --hgmd-ht-path gs://seqr-reference-data-private/GRCh37/HGMD/hgmd_pro_2018.4_hg19_without_db_field.ht --sample-type WES --es-host elasticsearch --es-index 1kg --es-index-min-num-shards 3 --vep-config-json-path /vep85-GRCh37-loftee-gcloud.json
```

Now that the dataset is loaded into elasticsearch, it can be added to the project:

1. Go to the project page
2. Click on Edit Datasets
3. Enter the index name that the pipeline printed out when it completed, and submit the form.

After this you can click "Variant Search" for each family, or "Gene Search" to search across families.


#### Enable read viewing in the browser (optional): 

To make .bam/.cram files viewable in the browser through igv.js, see **[ReadViz Setup Instructions](deploy/READVIZ_SETUP.md)**      
