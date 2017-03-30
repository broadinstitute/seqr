https://github.com/kubernetes/kubernetes/tree/master/examples


https://kubernetes.io/docs/tutorials/stateless-application/hello-minikube/


Installation
------------

seqr consists of several standalone components:
- web application - written in python, django.
- matchbox - 


Recommended approach:
 Kubernetes - 
    - local development - currently there are two popular ways to set up a local kubernetes cluster:
        `minicube` is the official 
                  rely on new low-overhead virtualization features built in to linux and the latest versions of MacOSX,
                    
                  - `minicube` - is the officially-supported approach for local installs. It uses 
                  
 

Other ways to install seqr:

 - `scripts` - Install all dependencies, databases and code directly onto the machine. 
   The bash scripts in `deploy/scripts` can be used as examples.  
   *Pro:* doesn't require docker or kubernetes  
   *Con:* each seqr component must be installed, configured and started manually. Also, some components
     may run into unexpected conflicts with existing software or python library versions on the machine.    
 - `docker` -  if [docker](https://docs.docker.com/docker-for-mac/) is installed on your machine, 
     the Dockerfiles under `deploy/docker` can be used to create containers for all seqr components.  
   *Pro:*  standardized installation of each component, isolated from other software.   
   *Con:*  containers must then be manually linked together to enable communication (eg. allowing the
      django/python container to connect to the database container, etc). Any subsequent vertical or horizontal 
      scaling must also be done manually.
 - `kubernetes`- recommend approach 
    *Pro:* kubernetes allows groups of docker containers to be deployed together in an automated, standardized way 
        and deals with a range of issues related to managing these deployments. For example, it allows a single
        deployment process and set of scripts to be reused essentially without modification both for production environments 
        (such as Google or AWS clouds) and for local or dev deployments (such as a virtualized kubernetes cluster 
    running locally on your dev machine).  
    *Con:*  requires learning about a number of new technologies, including docker.
 

https://kubernetes.io/docs/tutorials/stateless-application/hello-minikube/
