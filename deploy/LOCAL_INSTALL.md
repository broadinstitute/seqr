The installation scripts work on MacOSX and Linux (CentOS7 or Ubuntu). 
We appreciate modifications that add support for other platforms.  


#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **2 CPUs**, **50 Gb disk space**  

 - *Software:*  
     - python2.7    
     - on MacOS only: [homebrew](http://brew.sh/) package manager  
     - on Linux only: root access with sudo
    

#### Step 1: Install dependencies

Run the following command to adjust system settings and install `gcc`, `java1.8`, and other dependencies on the host machine (using `brew`, `yum` or `apt-get`):

```
SCRIPT=install_general_dependencies.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

#### Step 1: Install seqr components

To install all components using one script, run

```
SCRIPT=install_local.all_steps.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```
which runs the `install_local.*.sh` scripts in this directory in order.  

To install components one at a time, run the `install_local.*.sh` manually. 
