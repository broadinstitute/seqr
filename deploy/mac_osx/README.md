
xBrowse: MacOSX Development Instance
====================================

The steps below can be used to set up an xBrowse development instance on your local MacOSX laptop or desktop.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
- [Prereqs](#prereqs)
- [Install](#install)
- [Load data](#load-data)
- [Start the Development Server](#start-the-development-server)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prereqs

Clone the xBrowse repo from github to somewhere on your machine:  
`git clone https://github.com/xbrowse/xbrowse.git`  
  
To make it easier to do the steps below, set XBROWSE_CODE_DIR in your ~/.bashrc to the cloned xBrowse directory:  
`export XBROWSE_CODE_DIR=[cloned xbrowse directory]`   (eg. mine is set to /Users/weisburd/code/xbrowse/)

## Install

NOTE: root access may be required for the brew install commands. 

0. Add xbrowse and xbrowse_settings to your PYTHONPATH in ~/.bashrc:
  `PYTHONPATH=${XBROWSE_CODE_DIR}:$PYTHONPATH`  
  `PYTHONPATH=${XBROWSE_CODE_DIR}/deploy/mac_osx/xbrowse_settings:$PYTHONPATH`
1. Go to the cloned xBrowse repo directory:  
   `cd $XBROWSE_CODE_DIR`
2. Download a tarball of test data and resources (it's 3.8GB, so may take a while).  
  While it's downloading, you may want to proceed to steps 2 to 6 in a separate terminal.  
  `wget ftp://atguftp.mgh.harvard.edu/xbrowse-laptop-downloads.tar.gz`  
  `tar -xzf xbrowse-laptop-downloads.tar.gz`  
3. Install [homebrew](http://brew.sh/) if it's not installed already. To check if already installed, try: `brew --version`.
3. Install python if it's not installed already:  
  `brew install python  # this should install python 2.7`  
  `easy_install pip  # installs the python package installer`  
4. Install MongoDB. This is a NoSQL database that will store large static datasets such as variants, annotations, etc.
  `brew install mongodb`  
  `brew services start mongodb`
  `mongod --dbpath <directory where you want to store db files> &  # start MongoDB in the background`
5. Install MySQL. A MySQL database isn't actually used, but the python mysql library (which is used to access Ensembl) requires MySQL to be installed.
  `brew install mysql`
5. Install VEP which will be used by xBrowse to annotate variants.  
  `cd ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/`  
  `tar xzf variant_effect_predictor.tar.gz`
  `mkdir vep_cache_dir;  tar xzf vep_cache_dir.tar.gz -C vep_cache_dir`  
  `cd variant_effect_predictor`  
  `perl INSTALL.pl`
6. Install python virtualenv. This allows specific versions of python libraries to be installed as needed for xBrowse 
  without interfering with previously-installed versions. To make virtualenv more user-friendly you may also wish to install  [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/) and use it instead of using virtualenv directly.  
  `cd ${XBROWSE_CODE_DIR}`
  `pip install virtualenv`  
  `virtualenv venv   # create the 'venv' directory which will contain the xBrowse python virtual environment`  
  `source ./venv/bin/activate  # activate the xBrowse virtual environment`  
7. Install python libraries needed for xBrowse.  
  `pip install -r server_requirements_prereqs.txt`  
  `pip install -r server_requirements.txt`  
     

## Load data

The Django command that creates the database xBrowse uses to store users and other website data is:

	./manage.py migrate

	 
It will ask you to create a username and password for the "superuser" - this is just stored locally, it can be anything.
Once the development website is running, you will use this username and password to "Sign in" to the website.

`syncdb` doesn't create any of the actual scientific resources. We need to run another command for that: 

	./manage.py load_resources

This will take ~20 minutes. (Note that there are multiple progress bars in sequence.)

xBrowse is now fully installed. You can visit http://localhost:8000 on your web browser and log in with the username you just created. 


Now we'll finally create an xBrowse project for analysis. Again from within the machine, run the following command: 

	./manage.py add_project 1kg

Now refresh xBrowse - you should see the project there. To add the individuals: 

	./manage.py add_individuals_to_project 1kg --ped ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.ped

And to add a VCF file: 

	./manage.py add_vcf_to_project 1kg ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.vcf

This links the VCF file to the project, but doesn't load the data. We need to run one final command to load everything: 

	./manage.py load_project 1kg

`load_project` will take ~1 hour - it has to parse all the variants from the VCF file, annotate them, and load them into the variant database. (Annotation is the time bottleneck.)


## Start the Development Server

To start the Django development server, run:
 
	./manage.py runserver 8000

Now you should see the development instance of xBrowse at [http://localhost:8000/], 

and should be able to login using the "superuser" username and password you entered during the "Loading data" steps above. 
