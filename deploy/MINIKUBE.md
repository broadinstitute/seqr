## Install

Whether installing seqr on a laptop, on-prem, or on cloud VMs, Docker images and Kubernetes can be used to automate the deployment steps and isolate them from the host systems. 

The instructions below cover local deployments using Minikube, but are also directly applicable to cloud-based deployments which replace Minikube with a managed Kubernetes cluster like Google Container Engine.
The Kubernetes project maintains a [complete list of deployment options](https://kubernetes.io/docs/setup/pick-right-solution/).

#### Prerequisites
 - *Hardware:*  At least **16 Gb RAM**, **2 CPUs**, **50 Gb disk space**  

 - *Software:*  
     - python2.7    
     - on MacOS only: [homebrew](http://brew.sh/) package manager  
     - on Linux only: root access with sudo
    

#### Step 1: Install Kubernetes

Local and on-prem installations can use [MiniKube](https://kubernetes.io/docs/setup/minikube/) to create a self-contained kubernetes cluster on a single machine.  

Run the following command to install `gcc`, `java1.8`, `minikube`, `kubectl` and their dependencies on the host machine (using `brew`, `yum` or `apt-get`):

```
SCRIPT=step1.linux-ubuntu18.install_dependencies.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

#### Step 2: Install and start elasticsearch

Run this command to start an elasticsearch instance in the current directory: 
```
SCRIPT=step2.install_and_start_elasticsearch.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

#### Step 3: Download seqr deployment scripts

In a new terminal, run this command to download seqr deployment scripts:
```
SCRIPT=step3.download_deployment_scripts.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```
  
Optionally edit deployment settings before proceeding to step 4:

* *deploy/kubernetes/minikube-settings.yaml* - contains settings like $MINIKUBE_DISK_SIZE.
* *deploy/secrets/shared/** - directories that contain keys, passwords and other sensitive info that shouldn't be shared publicly. You may at some point want to edit:
  * *gcloud/service-account-key.json* - allows gcloud and kubectl to access google cloud resources in your project from within pods. We provide a placeholder key which can access public resources.
  * *nginx/tls.cert* and *nginx/tls.key* - ssh keys that allow https access and avoid web browser "insecure website" warnings. https connections are critical for encrypting seqr logins, so you will want to order your own keys before making your seqr instance visible over the internet.
  * *seqr/postmark_server_token* - seqr uses this to send outgoing emails via postmark.com mail service
  * *seqr/omim_key* - api key for downloading the latest omim files. We provide a placeholder key, but you'll want to use your own.
  * *matchbox/nodes.json* - contains the list of all nodes that matchbox can connect to on the MME network, along with the authentication token for each node.


#### Step 4: Install seqr on minikube

Run this command to deploy all seqr components to minikube and load reference data:

```
SCRIPT=step4.install_seqr_on_minikube.sh && curl -L http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

This step may run for 1 to 1.5 hours depending on internet speed. 


#### Create superuser 

After this finishes, you can create a super-user account by running these commands in the `seqr` subdirectory:

```
source ./activate_virtualenv.sh
  
./servctl create-user minikube 
```

#### Open seqr in browser

Then, to open seqr in your browser, you can do: 

```
open http://$(minikube ip):30003   
```

assuming you are on MacOS and minikube is running on the same machine as the web browser.

If minikube is running on a remote machine and you want to access seqr over the internet, you will need to first make sure 
traffic is being forwarded from the remote machine's http port (port 80) to seqr's Node port in minikube (30003). One way to do this is to start 
an ssh tunnel on the machine that's running minikube:

```
sudo ssh -v -i ~/.ssh/id_rsa -N -L 0.0.0.0:80:localhost:30003 ${USER}@$(hostname)
```   

NOTE: If you encounter `Permission denied (publickey)` errors, you may need to [generate ssh keys](https://help.github.com/enterprise/2.14/user/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/#generating-a-new-ssh-key) and do `cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys` before starting the tunnel.   


## Load example project

To create an example seqr project and load an exome dataset with 16 individuals from the 1000 genomes project, run: 

```
source ./activate_virtualenv.sh

./servctl load-example-project --cpu-limit 1 minikube
```

This can take 16 to 24 hours on a machine with 16 Gb RAM and using 1 CPU for annotation. 
If more memory is available, raising the `--cpu-limit` will allow multiple instances of VEP to run in parallel (with each VEP instance needing ~4 Gb additional RAM), 
and parallelize all other steps in the pipeline, with a proportional reduction in runtime.     


## Creating projects and loading datasets

A seqr project groups together users that are collaborating on the analysis of one or more datasets. It encapsulates the variant data, pedigree information, and any tags or notes that users create during analysis.
  
To create a new project:  
1. login to seqr and click on `+ Create Project` in the bottom right.  
2. click on the new project. Also, note the project GUID in the url `/project/${project_guid}/project_page` - for example `R0003_demo_project1`
3. click `Edit Families and Individuals` and use the Bulk Upload form to upload a pedigree file in [.fam format](https://www.cog-genomics.org/plink2/formats#fam)  
   
To annotate and load a new dataset, run the `servctl load-dataset` command. For example: 
```
source ./activate_virtualenv.sh

./servctl load-dataset minikube --genome-version 37 --project-guid "${project_guid}" --sample-type WES --dataset-type VARIANTS --cpu-limit 1 --input-vcf ${vcf_path} 
``` 

where `${vcf_path}` is replaced with `/local/path/to/your_data.vcf.gz` or `gs://some-google-storage-bucket/path/to/your_data.vcf.gz`, and `${project_guid}` comes from the project page url.

Once the dataset finishes loading, you can add it to a seqr project using the `Edit Datasets` form on the Project page. 

