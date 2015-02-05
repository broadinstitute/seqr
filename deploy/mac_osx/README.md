
xBrowse: MacOSX Development Instance
====================================

The steps below can be used to set up an xBrowse development instance on your local MacOSX laptop or desktop.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
- [Prereqs](#prereqs)
- [Install](#install)
- [Load data](#load-data)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prereqs

Choose or create a directory where you want to install xbrowse. 
In your terminal, set the envirnoment variable:  

`export XBROWSE_INSTALL_DIR=[directory where to install xbrowse]` 

This variable is only used during the install, but it's good to add it 
to your `~/.bashrc` anyway. 
That way you'll be able to just copy-pasteother lines in the install 
instructions below that need to be copied to your `~/.bashrc` and are defined 
relative to `${XBROWSE_INSTALL_DIR}`. 

## Install

NOTE: root access may be required for the brew install commands. 

0. Install [homebrew](http://brew.sh/) if it's not installed already. To check if already installed, try: `brew --version`.

1. Create xbrowse sub-directory structure:
   `mkdir ${XBROWSE_INSTALL_DIR}/code  ${XBROWSE_INSTALL_DIR}/data`
  
2. Download the xbrowse data tarball (411Mb). It contains reference data + an example project based on 1000 genomes data.

   `cd ${XBROWSE_INSTALL_DIR}/data;  wget ftp://atguftp.mgh.harvard.edu/xbrowse-resource-bundle.tar.gz;  tar -xzf xbrowse-resource-bundle.tar.gz` 
    While it's downloading, you may want to proceed with the next steps in a new terminal.  
  
3. Download and install VEP. It's used by xBrowse to annotate variants. Also, we install tabix as we need it to optimize the VEP cache.
   `brew install tabix`
   `cd ${XBROWSE_INSTALL_DIR};  wget https://github.com/Ensembl/ensembl-tools/archive/release/78.zip`
   `unzip 78.zip; mv ensembl-tools-release-78/scripts/variant_effect_predictor .; rm -rf 78.zip ensembl-tools-release-78`
   `cd variant_effect_predictor; perl INSTALL.pl --AUTO acf --CACHEDIR ../vep_cache_dir --SPECIES homo_sapiens --ASSEMBLY  GRCh37 --CONVERT`
   While it's installing, you may want to proceed with the next steps in a new terminal. 

4. Install MongoDB. This is a NoSQL database that will hold large static datasets such as variants, annotations, etc.
   `brew install mongodb`  
   `brew services start mongodb`
   `mongod --dbpath <directory where you want to store db files> &  # start MongoDB in the background`

5. Install MySQL. A MySQL database isn't actually used, but the python mysql library (which is used to access Ensembl) requires MySQL to be installed.
   `brew install mysql`

6. Install python v2.7 if it's not installed already:  
   `brew install python  # this should install python 2.7`  
   `easy_install pip  # installs the python package installer`  

7. Install python virtualenv and virtualenvwrapper. This allows specific versions of python libraries to be installed as needed for xBrowse without interfering with previously-installed libraries.
   `pip install virtualenvwrapper`

   and add these lines to your `~/.bashrc`:
   `export VIRTUALENVWRAPPER_VIRTUALENV_ARGS='--no-site-packages'  #  ensure that all new environments are isolated from the system site-packages directory`
   `export WORKON_HOME=$HOME/.virtualenvs`
   `export PROJECT_HOME=$HOME/code`
   `source /usr/local/bin/virtualenvwrapper.sh`

8. Create a virtualenv and install all needed python libraries.
   `workon xbrowse`
   `pip install -r server_requirements_prereqs.txt`  
   `pip install -r server_requirements.txt`  

9. Clone the xbrowse repo from github:
   `cd ${XBROWSE_INSTALL_DIR}/code;  git clone https://github.com/xbrowse/xbrowse.git`
  
    and add these lines to your `~/.bashrc`:
   `export PYTHONPATH=${XBROWSE_INSTALL_DIR}/code/xbrowse:$PYTHONPATH`  
   `export PYTHONPATH=${XBROWSE_INSTALL_DIR}/code/xbrowse/deploy/mac_osx/xbrowse_settings:$PYTHONPATH`
  

## Load data

1. Run a Django command to create the database xBrowse uses for storing users, project and other metatada
   `./manage.py migrate`

  It will ask you to create a username and password for a "superuser". This user will have access to all xBrowse projects on your development instance. Later you will be able to create other such superusers if needed. Once the development website is up and running, you can use this username and password you enter here to "Log in" to the development website.

2. Load reference data from ${XBROWSE_INSTALL_DIR}/data/reference_data into the database
   `./manage.py load_resources`

  This will take ~20 minutes. Several progress bars will show in sequence.
3. Start the development server which comes with Django
   `./manage runserver 8000`
    You can now open [http://localhost:8000] in your browser and see the projects.

4. Load the 1kg example project into the database
   `./manage.py add_project 1kg`
   If you refresh xBrowse, you should see the project appear there. 

5. Add individuals to the project: 
   `./manage.py add_individuals_to_project 1kg --ped ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.ped`

6. Add the VCF file: 
   `./manage.py add_vcf_to_project 1kg ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.vcf`
   This adds a pointer to the VCF file in the database, but doesn't actually load it. 

7. To load the VCF file: 
   `./manage.py load_project 1kg`

   This should take ~1 hour - it has to parse all the variants from the VCF file, annotate them, and load them into the variant database. (Annotation is the time bottleneck.)

