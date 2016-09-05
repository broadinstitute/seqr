
seqr: MacOSX Development Instance
====================================

The steps below can be used to set up a development instance of seqr.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
- [Prereqs](#prereqs)
- [Install](#install)
- [Load data](#load-your-own-data)
- [Production environment](#production-environment)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prereqs

Choose or create a directory where you want to install seqr. 
In your terminal, set the envirnoment variable:  

`export SEQR_INSTALL_DIR=[directory where to install seqr]`   

This variable is only used during the install, but it's good to add it 
to your `~/.bashrc` anyway. 
That way you can just copy-paste other lines from the instructions below to your `~/.bashrc` since they are defined 
relative to `${SEQR_INSTALL_DIR}`. 

## Install

NOTE: root access may be required for the brew install commands. 

0. Install [homebrew](http://brew.sh/) if it's not installed already. To check if it's already installed, run: `brew --version`.  
  
0. Create subdirectories:  
   `cd ${SEQR_INSTALL_DIR}`  
   `mkdir  code  data  data/reference_data  data/projects  data/reference_data/omim`  
  
0. Download seqr reference data. You may want to download these in the background while proceeding to next steps. 
    - `cd ${SEQR_INSTALL_DIR}/data/reference_data`  
    - `wget http://seqr.broadinstitute.org/static/bundle/seqr-resource-bundle.tar.gz;  tar -xzf seqr-resource-bundle.tar.gz`  
    - `wget http://seqr.broadinstitute.org/static/bundle/dbNSFP.gz; wget http://seqr.broadinstitute.org/static/bundle/dbNSFP.gz.tbi; `
    - `wget http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz`  
    - `wget http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz`  
    - `cd ${SEQR_INSTALL_DIR}/data/reference_data/omim` . Then download the `genemap2.txt` and `mim2gene.txt` files from [OMIM](http://www.omim.org/downloads) (this may require free registration).
    
    `cd ${SEQR_INSTALL_DIR}/data/projects`  
    `wget http://seqr.broadinstitute.org/static/bundle/1kg_project.tar.gz;  tar -xzf 1kg_project.tar.gz`  


0. Download and install VEP. It's used by seqr to annotate variants. Also, we install tabix as we need it to optimize the VEP cache.  
   `brew install tabix`  
   `cd ${SEQR_INSTALL_DIR}`  
   `wget https://github.com/Ensembl/ensembl-tools/archive/release/81.zip`  
   `unzip 81.zip`  
   `mv ensembl-tools-release-81/scripts/variant_effect_predictor .`  
   `rm -rf 81.zip ensembl-tools-release-81`  
   `cd variant_effect_predictor`  
   `perl INSTALL.pl --AUTO acf --CACHEDIR ../vep_cache --SPECIES homo_sapiens --ASSEMBLY  GRCh37 --CONVERT`  

   While it's installing, you may want to proceed with the next steps in a new terminal.  

0. Install MongoDB. This is a NoSQL database that will hold large static datasets such as variants, annotations, etc.  
   `brew install mongodb`  
   `brew services start mongodb`  
   `mongod --dbpath <directory where you want to store db files> &    # start MongoDB in the background`  

0. Install MySQL. A MySQL database isn't actually used, but the python mysql library (which is used to access Ensembl) requires MySQL to be installed.  
   `brew install mysql`  
  
0. Install python v2.7 if it's not installed already:  
   `brew install python    # this should install python 2.7`  
   `easy_install pip       # installs the python package installer`  
  
0. Clone the seqr repo from github:  
   `cd ${SEQR_INSTALL_DIR}/code`  
   `git clone https://github.com/seqr/seqr.git`  

   and add these lines to your `~/.bashrc`:  
   `export PYTHONPATH=${SEQR_INSTALL_DIR}/code/seqr:$PYTHONPATH`  
   `export PYTHONPATH=${SEQR_INSTALL_DIR}/code/seqr/deploy/mac_osx/xbrowse_settings:$PYTHONPATH`  

0. Install python virtualenv and virtualenvwrapper. This allows specific versions of python libraries to be installed as needed for seqr without interfering with previously-installed libraries.  
   `/usr/local/bin/pip install virtualenvwrapper`  

   and add these lines to your `~/.bashrc`:  
   `export VIRTUALENVWRAPPER_VIRTUALENV_ARGS='--no-site-packages'  #  isolate new environments from global site-packages directory`  
   `export WORKON_HOME=$HOME/.virtualenvs`  
   `source /usr/local/bin/virtualenvwrapper.sh`  
  
0. Create a virtualenv and install all needed python libraries.  
   `mkvirtualenv seqr`  
   `cd ${SEQR_INSTALL_DIR}/code/seqr`  
   `pip install -r requirements.txt`  


## Load example data

0. Switch to the seqr virtualenv.  
   `cd ${SEQR_INSTALL_DIR}/code/seqr`  
   `workon seqr`  
   
0. Initialize the database. This django command creates the database seqr uses for storing users, projects and other metatada.  
   `./manage.py migrate`  

0. Load data from ${SEQR_INSTALL_DIR}/data/reference_data into the database.  
   `./manage.py load_resources`  
   
  This will take ~20 minutes (a sequence of progress bars will show).  
  While it's loading, you may want to proceed with the next steps in a new terminal (but remember to repeat all of step 1).

0.  To load the OMIM data, run:  
   `./manage.py load_omim`  

0. Create superuser(s). This user will have access to all seqr projects on your development instance.  
   `./manage.py createsuperuser   # it will ask you to create a username and password`  

0. Start the development server:  
   `./manage.py runserver 8000`  

    You can now open [http://localhost:8000](http://localhost:8000) in your browser and login using the superuser credentials.  

0. Create the 1kg example project:  
   `./manage.py add_project 1kg`  
   
   If you now refresh [http://localhost:8000](http://localhost:8000), you should see the project appear.  

0. Initialize the project with the example data we downloaded earlier:  
   `./manage.py load_project_dir 1kg ${SEQR_INSTALL_DIR}/data/projects/1kg_project`  
   
   This adds the file paths to the database, but doesn't actually load the VCF data.  

0. To load the VCF data:
   `./manage.py load_project 1kg`



## Load your own data

0. seqr was designed around the format of VCFs produced by the GATK variant calling tools.
   * the following genotype format is expected: GT:AD:DP:GQ:PL

0. Before a VCF can be loaded into seqr, it must be annotated with VEP to add a specific set of annotations, including those provided by the [dbNSFP](http://www.ensembl.info/ecode/loftee/) and [LoFTEE](http://www.ensembl.info/ecode/loftee/) plugins. Once these plugins have been installed, please use the following command to annotate your VCF file (here called my_data.vcf.gz): 
 
   ```perl ./vep/ensembl-tools-release-81/scripts/variant_effect_predictor/variant_effect_predictor.pl --everything --vcf --allele_number --no_stats --cache --offline --dir ./vep_cache/ --force_overwrite --cache_version 81 --fasta ./vep_cache/homo_sapiens/81_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa --assembly GRCh37 --tabix --plugin LoF,human_ancestor_fa:./loftee_data/human_ancestor.fa.gz,filter_position:0.05,min_intron_size:15 --plugin dbNSFP,./reference_data/dbNSFP/dbNSFPv2.9.gz,Polyphen2_HVAR_pred,CADD_phred,SIFT_pred,FATHMM_pred,MutationTaster_pred,MetaSVM_pred -i my_data.vcf.gz -o my_data.vep.vcf.gz```

   NOTE: VEP tends to run out of memory on large VCFs, so it's best to split the vcf into chuncks with 5000 or fewer variants in each,
  run VEP on each chunk in parallel, and then recombine. The [grabix](https://github.com/arq5x/grabix) indexing tool is very helpful for the splitting step because it lets you extract an arbitrary range of lines from the vcf, and these can be piped directly into VEP. 
  
0. Once you have an annotated file, it can be loaded the same way as steps 6 to 8 in the 'Load example data' section. 



## Production Environment

0. Web server: For production, we recommend running either Apache with mod_wsgi, or [gunicorn](https://pypi.python.org/pypi/gunicorn/) with [nginx](http://nginx.org/en/) as a reverse proxy. An example gunicorn and nginx configuration is [described here](https://github.com/macarthur-lab/seqr/blob/master/deploy/production_config_example.md). A good tutorial on the gunicorn+nginx setup can be found here: http://agiliq.com/blog/2013/08/minimal-nginx-and-gunicorn-configuration-for-djang/


1. It's critical to enable *https* in the apache or nginx config to prevent login credentials and other sensative information from being sent in plain text. 
