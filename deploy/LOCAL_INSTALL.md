#### Prerequisites
- *Hardware:*  At least **16 Gb RAM**, **4 CPUs**, **50 Gb disk space**  

- *Software:* 
  - [docker](https://docs.docker.com/install/)
   
    - under Preferences > Resources > Advanced set the memory limit to at least 12 Gb

  - [docker-compose](https://docs.docker.com/compose/install/)       
   
  - [gcloud](https://cloud.google.com/sdk/install)

- OS settings for elasticsearch:
  - **Linux only:** elasticsearch needs [higher-than-default virtual memory settings](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html). To adjust this, run   
  ```bash
  echo '
     vm.max_map_count=262144
  ' | sudo tee -a /etc/sysctl.conf
      
  sudo sysctl -w vm.max_map_count=262144
  ```
  This will prevent elasticsearch start up error: `max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]`
    

#### Starting seqr

The steps below describe how to create a new empty seqr instance with a single Admin user account.

```bash
SEQR_DIR=$(pwd)

wget https://raw.githubusercontent.com/broadinstitute/seqr/master/docker-compose.yml

docker-compose up -d seqr   # start up the seqr docker image in the background after also starting other components it depends on (postgres, redis, elasticsearch). This may take 10+ minutes.
docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 

docker-compose exec seqr python manage.py createsuperuser  # create a seqr Admin user 

open http://localhost     # open the seqr landing page in your browser. Log in to seqr using the email and password from the previous step
```

#### Updating seqr

Updating your local installation of seqr involves pulling the latest version of the seqr docker container, and then recreating the container.

```bash
# run this from the directory containing your docker-compose.yml file
docker-compose pull
docker-compose up -d seqr

docker-compose logs -f seqr  # (optional) continuously print seqr logs to see when it is done starting up or if there are any errors. Type Ctrl-C to exit from the logs. 
```

To update reference data in seqr, such as OMIM, HPO, etc., run the following
```bash
docker-compose exec seqr manage.py update_all_reference_data --use-cached-omim --skip-gencode
```
   
#### Annotating and loading VCF callsets 

##### Option #1: annotate on a Google Dataproc cluster, then load in to an on-prem seqr instance 

Google Dataproc makes it easy to start a spark cluster which can be used to parallelize annotation across many machines.
The steps below describe how to annotate a callset and then load it into your on-prem elasticsearch instance.

1. authenticate into your google cloud account.
   ```bash
   gcloud auth application-default login  
   ```

1. upload your .vcf.gz callset to a google bucket
   ```bash
   GS_BUCKET=gs://your-bucket       # your google bucket
   GS_FILE_PATH=data/GRCh38         # the desired file path. Good to include build version and/ or sample type to directory structure
   FILENAME=your-callset.vcf.gz     # the local file you want to load  
    
   gsutil cp $FILENAME $GS_BUCKET/$GS_FILE_PATH
   ```
   
1. start a pipeline-runner container which has the necessary tools and environment for starting and submitting jobs to a Dataproc cluster.
   ```bash
   docker-compose up -d pipeline-runner            # start the pipeline-runner container 
   ```
   
1. if you haven't already, upload reference data to your own google bucket. 
This should be done once per build version, and does not need to be repeated for subsequent loading jobs.
This is expected to take a while
   ```bash
   BUILD_VERSION=38                 # can be 37 or 38
    
   docker-compose exec pipeline-runner copy_reference_data_to_gs.sh $BUILD_VERSION $GS_BUCKET
   
   ```
   Periodically, you may want to update the reference data in order to get the latest versions of these annotations. 
To do this, run the following commands to update the data. All subsequently loaded data will then have the updated 
annotations, but you will need to re-load previously loaded projects to get the updated annotations.
   ```bash
   GS_BUCKET=gs://your-bucket       # your google bucket
   BUILD_VERSION=38                 # can be 37 or 38
   
   # Update clinvar 
   gsutil rm -r "${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}/clinvar.GRCh${BUILD_VERSION}.ht"
   gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/clinvar/clinvar.GRCh${BUILD_VERSION}.ht" "${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}/clinvar.GRCh${BUILD_VERSION}.ht"
  
   # Update all other reference data
   gsutil rm -r "${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}/combined_reference_data_grch${BUILD_VERSION}.ht"
   gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/all_reference_data/combined_reference_data_grch${BUILD_VERSION}.ht" "${GS_BUCKET}/reference_data/GRCh${BUILD_VERSION}/combined_reference_data_grch${BUILD_VERSION}.ht"
    ```

1. run the loading command in the pipeline-runner container. Adjust the arguments as needed
   ```bash
   BUILD_VERSION=38                 # can be 37 or 38
   SAMPLE_TYPE=WES                  # can be WES or WGS
   INDEX_NAME=your-dataset-name     # the desired index name to output. Will be used later to link the data to the corresponding seqr project
    
   INPUT_FILE_PATH=/${GS_FILE_PATH}/${FILENAME}  
    
   docker-compose exec pipeline-runner load_data_dataproc.sh $BUILD_VERSION $SAMPLE_TYPE $INDEX_NAME $GS_BUCKET $INPUT_FILE_PATH
   
   ``` 
   
##### Option #2: annotate and load on-prem

Annotating a callset with VEP and reference data can be very slow - as slow as several variants / sec per CPU, so although it is possible to run the pipeline on a single machine, it is recommended to use multiple machines.

The steps below describe how to annotate a callset and then load it into your on-prem elasticsearch instance.

1. create a directory for your vcf files. docker-compose will mount this directory into the pipeline-runner container.

   ```bash
   mkdir ./data/input_vcfs/ 
    
   FILE_PATH=GRCh38                 # the desired file path. Good to include build version and/ or sample type to directory structure
   FILENAME=your-callset.vcf.gz     # the local file you want to load. vcfs should be bgzip'ed
    
   cp $FILENAME ./data/input_vcfs/$FILE_PATH
   ```

1. start a pipeline-runner container
   ```bash
   docker-compose up -d pipeline-runner            # start the pipeline-runner container 
   ```
   
1. if you haven't already, download VEP and other reference data to the docker image's mounted directories. 
This should be done once per build version, and does not need to be repeated for subsequent loading jobs.
This is expected to take a while
   ```bash
   BUILD_VERSION=38                 # can be 37 or 38
    
   docker-compose exec pipeline-runner download_reference_data.sh $BUILD_VERSION
   
   ``` 
   Periodically, you may want to update the reference data in order to get the latest versions of these annotations. 
To do this, run the following commands to update the data. All subsequently loaded data will then have the updated 
annotations, but you will need to re-load previously loaded projects to get the updated annotations.
   ```bash
   BUILD_VERSION=38                 # can be 37 or 38
   
   # Update clinvar 
   docker-compose exec pipeline-runner rm -rf "/seqr-reference-data/GRCh${BUILD_VERSION}/clinvar.GRCh${BUILD_VERSION}.ht"
   docker-compose exec pipeline-runner gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/clinvar/clinvar.GRCh${BUILD_VERSION}.ht" "/seqr-reference-data/GRCh${BUILD_VERSION}/clinvar.GRCh${BUILD_VERSION}.ht"
  
   # Update all other reference data
   docker-compose exec pipeline-runner rm -rf "/seqr-reference-data/GRCh${BUILD_VERSION}/combined_reference_data_grch${BUILD_VERSION}.ht"
   docker-compose exec pipeline-runner gsutil rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/all_reference_data/combined_reference_data_grch${BUILD_VERSION}.ht" "/seqr-reference-data/GRCh${BUILD_VERSION}/combined_reference_data_grch${BUILD_VERSION}.ht"
    ```

1. run the loading command in the pipeline-runner container. Adjust the arguments as needed
   ```bash
   BUILD_VERSION=38                 # can be 37 or 38
   SAMPLE_TYPE=WES                  # can be WES or WGS
   INDEX_NAME=your-dataset-name     # the desired index name to output. Will be used later to link the data to the corresponding seqr project
    
   INPUT_FILE_PATH=${FILE_PATH}/${FILENAME}  
    
   docker-compose exec pipeline-runner load_data.sh $BUILD_VERSION $SAMPLE_TYPE $INDEX_NAME $INPUT_FILE_PATH
   
   ``` 

#### Adding a loaded dataset to a seqr project

After the dataset is loaded into elasticsearch, it can be added to your seqr project with these steps:

1. Go to the project page
1. Click on Edit Datasets
1. Enter the elasticsearch index name (the `$INDEX_NAME` argument you provided at loading time), and submit the form.

#### Enable read viewing in the browser (optional)

To make .bam/.cram files viewable in the browser through igv.js, see **[ReadViz Setup Instructions](https://github.com/broadinstitute/seqr/blob/master/deploy/READVIZ_SETUP.md)**      
