xBrowse: MacOSX Development Instance
====================================

The steps below can be used to set up an xBrowse development instance on your local MacOSX laptop or desktop.


## Prerequisites

* Install [homebrew](http://brew.sh/)
* Clone the xBrowse repo from github to somewhere on your machine:  
  `git clone https://github.com/xbrowse/xbrowse.git`  
  To make it easier to follow the steps below, set XBROWSE_CODE_DIR to the cloned directory and add it to your ~/.bashrc:  
  `export XBROWSE_CODE_DIR=[cloned xbrowse directory]`   (eg. mine is set to /Users/weisburd/code/xbrowse/)

## Installation

NOTE: root access may be required for the brew install commands. 

0. Go to the directory where the code was checked out:  
   `cd $XBROWSE_CODE_DIR`
1. Add xbrowse and xbrowse_settings to your PYTHONPATH in ~/.bashrc:
  `PYTHONPATH=${XBROWSE_CODE_DIR}:$PYTHONPATH`  
  `PYTHONPATH=${XBROWSE_CODE_DIR}/deploy/other/mac_osx/xbrowse_settings:$PYTHONPATH`
2. Download a tarball of test data and resources. It's 3.8GB, so may take a while...  
  (while it's downloading, you may want to proceed to steps 2 to 6 in a separate terminal)
  `wget ftp://atguftp.mgh.harvard.edu/xbrowse-laptop-downloads.tar.gz`  
  `tar -xzf xbrowse-laptop-downloads.tar.gz`  
  `cd xbrowse-laptop-downloads/`  
  `tar -xzf vep_cache_dir.tar.gz`  
  When this is done, you should see an `${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/homo_sapiens` directory.
3. Make sure python is installed:  
  `brew install python  # Python 2.7`  
  `easy_install pip  # Python package installer`  
4. Install MongoDB. This is a NoSQL database that will store project data such as variants, annotations, etc.
  `brew install mongodb`  
  `brew services start mongodb`  
  To configure the database storage directory, log directory, and other settings, edit the file:  
  `~/Library/LaunchAgents/homebrew.mxcl.mongodb.plist`  and then restart via `brew services restart mongodb`.  
  For an example, see the file: `${XBROWSE_CODE_DIR}/deploy/other/mac_osx/org.mongo.mongod.plist`  
5. Install VEP which will be used by xBrowse to annotate variants.  
  `cd ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/`  
  `tar xzf variant_effect_predictor.tar.gz`  
  `tar xzf vep_cache_dir.tar.gz`  
  `cd variant_effect_predictor`  
  `perl INSTALL.pl`  
6. Install python virtualenv. This allows specific versions of python libraries to be installed as needed for xBrowse 
  without interfering with already-installed versions. To make virtualenv more user-friendly you may wish to install and 
  use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/) instead.  
  `pip install virtualenv`  
  `virtualenv venv   # create the 'venv' directory which will contain the xBrowse python virtual environment`  
  `source ./venv/bin/activate  # activate the xBrowse virtual environment`  
7. Install python libraries needed for xBrowse.
  `pip install --user -r server_requirements_prereqs.txt`  
  `pip install --user -r server_requirements.txt`  
     

## Loading data

The Django command that creates the database xBrowse uses to store users and other website data is:

	`./manage.py syncdb --all`

	 
It will ask you to create a username and password for the "superuser" - this is just stored locally, it can be anything.
Once the local webserver is up and running, you will use this username and password to "Sign in" on the website.

`syncdb` doesn't create any of the actual scientific resources. We need to run another command for that: 

	`./manage.py load_resources`

This will take ~20 minutes. (Note that there are multiple progress bars in sequence.)

xBrowse is now fully installed. You can visit http://localhost:8000 on your web browser and log in with the username you just created. 


Now we'll finally create an xBrowse project for analysis. Again from within the machine, run the following command: 

	`./manage.py add_project 1kg`

Now refresh xBrowse - you should see the project there. To add the individuals: 

	`./manage.py add_individuals_to_project 1kg --ped ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.ped`

And to add a VCF file: 

	`./manage.py add_vcf_to_project 1kg ${XBROWSE_CODE_DIR}/xbrowse-laptop-downloads/1kg.vcf`

This links the VCF file to the project, but doesn't load the data. We need to run one final command to load everything: 

	`./manage.py load_project 1kg`

`load_project` will take ~1 hour - it has to parse all the variants from the VCF file, annotate them, and load them into the variant database. (Annotation is the time bottleneck.)


## Running the server

To start the Django development server, run:
 
`./manage.py runserver 8000` 

Now you should see the development instance of xBrowse at [http://localhost:8000/], 

and can login using the "superuser" username and password created during the "Loading data" steps above. 
