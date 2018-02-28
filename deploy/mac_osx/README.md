seqr: MacOSX Installation
====================================

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
- [Prereqs](#prereqs)
- [Installation](#install)
- [Loading datasets](#loading-your-own-datasets)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prereqs

Choose a directory where you want to install seqr.  
Then, set a SEQR_INSTALL_DIR envirnoment variable in your terminal to make the installation steps easier to follow:  

`export SEQR_INSTALL_DIR=[directory where to install seqr]`   
 

## Install

1. If it's not installed already, install [homebrew](http://brew.sh/) - the MacOS package manager.  
  
1. Create subdirectories:  
   `cd ${SEQR_INSTALL_DIR}`  
   `mkdir  code  data  data/reference_data  data/projects  data/reference_data/omim`  
  
1. Download seqr reference data. This can be done in a separate terminal while doing the next steps. 
    - `cd ${SEQR_INSTALL_DIR}/data/reference_data`  
    - `wget http://seqr.broadinstitute.org/static/bundle/seqr-resource-bundle.tar.gz;  tar -xzf seqr-resource-bundle.tar.gz`  
    - `wget http://seqr.broadinstitute.org/static/bundle/dbNSFP.gz; wget http://seqr.broadinstitute.org/static/bundle/dbNSFP.gz.tbi; `
    - `wget http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz`  
    - `wget http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz`  
    - `cd ${SEQR_INSTALL_DIR}/data/reference_data/omim` . Then download the `genemap2.txt` and `mim2gene.txt` files from [OMIM](http://www.omim.org/downloads) (this may require free registration).
    
    `cd ${SEQR_INSTALL_DIR}/data/projects`  
    `wget http://seqr.broadinstitute.org/static/bundle/1kg_project.tar.gz;  tar -xzf 1kg_project.tar.gz`  

1. Install python v2.7 if it's not installed already:  
   ```
   brew install python           # install python 2.7
   easy_install --user pip       # install pip the python package installer
   ```
  
1. Install MongoDB.  
   ```
   brew install mongodb
   brew services restart mongodb
   mongo       # open mongo client to check that you can now connect to mongo - then type Ctrl-D to exit
   ```
1. Install Postgres.  
   ```
   brew install postgres
   brew services start postgres
   psql -U postgres     # open postgres client to check that you can now connect to postgres - then type Ctrl-D to exit


1. Install [PhenoTips](https://phenotips.org/) for storing structured phenotype information.  
   ```
   wget https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/1.3.6/phenotips-standalone-1.3.6.zip`
   unzip phenotips-standalone-1.3.6.zip
   rm phenotips-standalone-1.3.6.zip
   cd phenotips-standalone-1.3.6
   ./start.sh
   ```
1. Clone the seqr repo from github:  
   ```
   cd ${SEQR_INSTALL_DIR}/code
   git clone https://github.com/macarthur-lab/seqr.git
   ```
   
   *then add these lines to your `~/.bashrc`:*    
   `export PYTHONPATH=${SEQR_INSTALL_DIR}/code/seqr:$PYTHONPATH`  
   `export PYTHONPATH=${SEQR_INSTALL_DIR}/code/seqr/deploy/mac_osx/xbrowse_settings:$PYTHONPATH`  

1. Install python virtualenv and virtualenvwrapper. This allows specific versions of python libraries to be installed as needed for seqr without interfering with previously-installed libraries.  
   `/usr/local/bin/pip install virtualenvwrapper`  

   *then add these lines to your `~/.bashrc`:*  
   `export VIRTUALENVWRAPPER_VIRTUALENV_ARGS='--no-site-packages'  #  isolate new environments from global site-packages directory`  
   `export WORKON_HOME=$HOME/.virtualenvs`  
   `source /usr/local/bin/virtualenvwrapper.sh`  
  
1. Create a virtualenv and install all needed python libraries.  
   `mkvirtualenv seqr`  
   `cd ${SEQR_INSTALL_DIR}/code/seqr`  
   `pip install -r requirements.txt`  


## Load example data

1. Switch to seqr virtualenv.  
   `cd ${SEQR_INSTALL_DIR}/code/seqr`  
   `workon seqr`  
   
1. Initialize the database. This django command creates the database seqr uses for storing users, projects and other metatada.  
   `./manage.py migrate`  

1. Load data from ${SEQR_INSTALL_DIR}/data/reference_data into the database.  
   `./manage.py load_resources`  
   
  This will take ~20 minutes (a sequence of progress bars will show).  
  While it's loading, you may want to proceed with the next steps in a new terminal (but remember to repeat all of step 1).

1.  To load the OMIM data, run:  
   `./manage.py load_omim`  

1. Create superuser(s). This user will have access to all seqr projects on your development instance.  
   `./manage.py createsuperuser   # it will ask you to create a username and password`  

1. Start the development server:  
   `./manage.py runserver 8000`  

    You can now open [http://localhost:8000](http://localhost:8000) in your browser and login using the superuser credentials.  

1. Create the 1kg example project:  
   `./manage.py add_project 1kg`  
   
   If you now refresh [http://localhost:8000](http://localhost:8000), you should see the project appear.  

1. Initialize the project with the example data we downloaded earlier:  
   `./manage.py load_project_dir 1kg ${SEQR_INSTALL_DIR}/data/projects/1kg_project`  
   
   This adds the file paths to the database, but doesn't actually load the VCF data.  

1. To load the VCF data:
   `./manage.py load_project 1kg`



## Loading your own datasets  

NOTE: seqr expects VCFs to have the following genotype format: GT:AD:DP:GQ:PL  


1. Before a VCF can be loaded into seqr, it must be annotated with VEP to add a specific set of annotations, including those provided by the [dbNSFP](http://www.ensembl.info/ecode/dbnsfp/) and [LoFTEE](http://www.ensembl.info/ecode/loftee/) plugins. Run the command below to install VEP. Also, it's useful to install tabix in order to optimize the VEP cache.  
   `brew install tabix`  
   `cd ${SEQR_INSTALL_DIR}`  
   `wget https://github.com/Ensembl/ensembl-tools/archive/release/85.zip`  
   `unzip 85.zip`  
   `mv ensembl-tools-release-81/scripts/variant_effect_predictor .`  
   `rm -rf 85.zip ensembl-tools-release-85`  
   `cd variant_effect_predictor`  
   `perl INSTALL.pl --AUTO acf --CACHEDIR ../vep_cache --SPECIES homo_sapiens --ASSEMBLY  GRCh37 --CONVERT`  

   While it's installing, you may want to proceed with the next steps in a new terminal.  


Once these plugins have been installed, please use the following command to annotate your VCF file (here called my_data.vcf.gz): 
 
   ```perl ./vep/ensembl-tools-release-85/scripts/variant_effect_predictor/variant_effect_predictor.pl --everything --vcf --allele_number --no_stats --cache --offline --dir ./vep_cache/ --force_overwrite --cache_version 81 --fasta ./vep_cache/homo_sapiens/81_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa --assembly GRCh37 --tabix --plugin LoF,human_ancestor_fa:./loftee_data/human_ancestor.fa.gz,filter_position:0.05,min_intron_size:15 --plugin dbNSFP,./reference_data/dbNSFP/dbNSFPv2.9.gz,Polyphen2_HVAR_pred,CADD_phred,SIFT_pred,FATHMM_pred,MutationTaster_pred,MetaSVM_pred -i my_data.vcf.gz -o my_data.vep.vcf.gz```

   NOTE: VEP tends to run out of memory on large VCFs, so it's best to split the vcf into chuncks with 5000 or fewer variants in each,
  run VEP on each chunk in parallel, and then recombine. The [grabix](https://github.com/arq5x/grabix) indexing tool is very helpful for the splitting step because it lets you extract an arbitrary range of lines from the vcf, and these can be piped directly into VEP. 
  
0. Once you have an annotated file, it can be loaded the same way as steps 6 to 8 in the 'Load example data' section. 

