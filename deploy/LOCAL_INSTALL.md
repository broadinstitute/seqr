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


#### Step 3: Create User, Login to seqr

To create an admin user, run:
```
cd ${SEQR_DIR}; python manage.py createsuperuser
```

To view seqr, open your browser to [http://localhost:8000/login](http://localhost:8000/login).


#### Step 5: Load Dataset

