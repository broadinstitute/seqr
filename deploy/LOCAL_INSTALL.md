The installation scripts work on MacOSX and Linux (CentOS7 or Ubuntu). 
We appreciate modifications that add support for other platforms.  


#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **2 CPUs**, **50 Gb disk space**  

 - *Software:*  
     - python2.7    
     - on MacOS only: [homebrew](http://brew.sh/) package manager  
     - on Linux only: root access with sudo
    

#### Step 1: Install dependencies

cd to the directory where you want to install seqr, and run: 

```
SCRIPT=install_general_dependencies.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
``` 

This command:
- clones the seqr repo to the current directory
- adds `PYTHONPATH`, `PLATFORM` and `SEQR_DIR` env. vars to .bashrc:
- adjusts system settings such as `vm.max_map_count` to work with elasticsearch
- uses brew/yum/apt-get to make sure `java1.8`, `gcc`, `git` and other dependencies are installed 

#### Step 2: Install seqr components

To install all components using one script, run:

```
SCRIPT=install_local.all_steps.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
```
This runs the `install_local.*.sh` scripts in order.  

To install components one at a time, run the `install_local.*.sh` scripts in order: 

```
SCRIPT=install_local.step1.install_mongo.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step2.install_postgres.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step3.elasticsearch.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step4.kibana.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step5.install_redis.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step6.load_reference_data.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step7.install_seqr.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step8.install_phenotips.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
SCRIPT=install_local.step9.install_pipeline_runner.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && ./$SCRIPT
```

Once these complete, the seqr gunicorn web server will be running on 0.0.0.0 port 8000. 


#### Step 3: Create admin. user

To create an admin user, run:
```
cd ${SEQR_DIR}; python manage.py createsuperuser
```


#### Step 4: Create a seqr project

A project in seqr represents a group of collaborators working together on one or more datasets.

1. Open your browser to [http://localhost:8000/login](http://localhost:8000/login)
2. Login using the account you entered in step 3. 
3. On the dashboard page, click on "Create Project".  
4. Click on the new project.
5. Click on Edit Families & Individuals > Bulk Upload and upload a .fam file with individuals for the project.


#### Step 5: Load dataset

To VEP-annotate and load a new VCF into Elasticsearch, run: 
```
source ~/.bashrc  
cd ${SEQR_DIR}/hail_elasticsearch_pipelines/  
  
GENOME_VERSION="37"        # should be "37" or "38"
SAMPLE_TYPE="WES"          # can be "WES" or "WGS"
DATASET_TYPE="VARIANTS"    # can be "VARIANTS" (for GATK VCFs) or "SV" (for Manta VCFs)
PROJECT_GUID="R001_test"   # should match the ID in the url of the project page 
INPUT_VCF="test.vcf.gz"    # local path of VCF file
 
python2.7 gcloud_dataproc/submit.py --run-locally hail_scripts/v01/load_dataset_to_es.py  --spark-home $SPARK_HOME --genome-version $GENOME_VERSION --project-guid $PROJECT_GUID --sample-type $SAMPLE_TYPE --dataset-type $DATASET_TYPE --skip-validation  --exclude-hgmd --vep-block-size 100 --es-block-size 10 --num-shards 1 --use-nested-objects-for-vep --use-child-docs-for-genotypes  $INPUT_VCF
```

Now that the dataset is loaded into elasticsearch, it can be added to the project:

1. Go to the projet page
2. Click on Edit Datasets
3. Enter the index name that the pipeline printed out when it completed, and submit the form.

After this you can click "Variant Search" for each family, or "Gene Search" to search across families.   