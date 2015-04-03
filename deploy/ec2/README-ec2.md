
xBrowse: Amazon Web Services
====================================

The steps below describe how to set up a fully isolated instance of xBrowse on Amazon Web Services.
We begin with vanilla CentOS 6.5 virtual machine,
and provision an xBrowse server that can be accessed over the public internet.

Although these steps are specific to AWS and CentOS 6.5,
they map closely to the steps you'd take to install xBrowse on other systems.
For example, this is a very similar process to how we administer xBrowse at the Broad Institute,
with a few modifications to accommodate specifics to our internal infrastructure.

Note that, though this is an AWS tutorial, we don't maintain any prebuilt AMIs at this time -
though you could use the result of this tutorial to package AMIs for internal use.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents** 

- [Prerequisite: AWS Account](#prerequisite-aws-account)
- [Create the virtual machine](#create-the-virtual-machine)
- [Provisioning the machine](#provisioning-the-machine)
- [Load Test Data](#load-test-data)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisite: AWS Account

Make sure that you have an AWS account.
This tutorial will not fall under the free usage tier, so you'll need a credit card.
It will only cost a few dollars if you delete everything right after,
but that last part is important - **make sure you terminate VMs that you aren't using**.

## Create the virtual machine

These instructions are sparse since there are multiple ways to create virtual machines on AWS.

0. Create a new EC2 Virtual Machine from Community AMI `ami-8997afe0`.
(Note: you must set your region to `us-east-1` for this AMI to appear in search results).
Use instance type `m3.medium`, or something more powerful.  
  
  At this point, you should be able to log into the machine:  
  
  `ssh -i /path/to/private/key root@url.of.machine`  

0. Create an EBS Volume with at least 50 GB storage. This is where all of the xBrowse data and database files will go.

0. Attach the EBS volume to the VM.

0. *Mount* the EBS volume to the VM. In this document, we assume that the volume is mounted to `/mnt`. One way is to run:  
    `lsblk   # this shows all devices that can be mounted along with their name and size`  
    `mkfs -t ext4 /dev/xvdl    # replace 'xvdl' with the name given by lsblk`  
    `mount -t ext4 /dev/xvdl /mnt`

Before continuing, make sure that the mountpoint is correctly set up - it should look something like this:

    $ df -H
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/xvde       8.5G  682M  7.4G   9% /
    tmpfs           2.0G     0  2.0G   0% /dev/shm
    /dev/xvdl        53G  189M   50G   1% /mnt

## Provisioning the machine

A bulk of the provisioning in xBrowse is performed by Puppet, but a few steps are run manually.
Log into the machine and do the following:

0. Update Yum  
    `yum update -y`

0. Install git and wget  
    `yum install git wget unzip -y`

0. Install Puppet  
    `rpm -Uvh http://yum.puppetlabs.com/el/6/products/i386/puppetlabs-release-6-7.noarch.rpm`  
    `yum -y -q install puppet`  

0. Create subdirectories:  
   `cd /mnt`  
   `mkdir -p code/xbrowse-settings data/reference_data data/projects mongodb`

0. Clone the xbrowse repo from github:  
   `cd /mnt/code`  
   `git clone https://github.com/xbrowse/xbrowse.git`  

0. Download necessary reference data from xBrowse and external sources.  
   `cd /mnt/data/reference_data`  
   `wget ftp://atguftp.mgh.harvard.edu/xbrowse-resource-bundle.tar.gz; tar -xzf xbrowse-resource-bundle.tar.gz`  
   `wget ftp://ftp.ncbi.nih.gov/snp/organisms/human_9606_b142_GRCh37p13/VCF/00-All.vcf.gz`  
   `wget ftp://dbnsfp:dbnsfp@dbnsfp.softgenetics.com/dbNSFPv2.9.zip;  unzip -d dbNSFP dbNSFPv2.9.zip`  
   `wget ftp://ftp.ncbi.nih.gov/pub/clinvar/vcf_GRCh37/clinvar.vcf.gz*`  
   `wget ftp://ftp.broadinstitute.org/pub/ExAC_release/release0.3/ExAC.r0.3.sites.vep.vcf.gz`  

   `cd /mnt/data/projects`  
   `wget ftp://atguftp.mgh.harvard.edu/1kg_project.tar.gz;  tar -xzf 1kg_project.tar.gz`  
    

0. Run Puppet to provision this machine for xBrowse. This takes a while (~2 hours) and performs a bulk of the provisioning.  
    `puppet apply /mnt/code/xbrowse/deploy/ec2/ec2_provision.pp --modulepath=/mnt/code/xbrowse/deploy/puppet/modules`  

0. Install Perl dependencies. Perl itself is installed in the Puppet command above,
but we must install the package manager and a few packages manually.  
(This should eventually be rolled into Puppet.)  
    `curl -L http://cpanmin.us | perl - --sudo App::cpanminus`  
    `cpanm Archive::Extract CGI Time::HiRes Archive::Zip Archive::Tar`  

0. Download and install VEP. It's used by xBrowse to annotate variants.  
(This also should eventually be rolled into Puppet.)  
   `cd /mnt`  
   `wget https://github.com/Ensembl/ensembl-tools/archive/release/78.zip`  
   `unzip 78.zip`  
   `mv ensembl-tools-release-78/scripts/variant_effect_predictor .`  
   `rm -rf 78.zip ensembl-tools-release-78`  
   `cd variant_effect_predictor`  
   `perl INSTALL.pl --AUTO acf --CACHEDIR ../vep_cache_dir --SPECIES homo_sapiens --ASSEMBLY  GRCh37 --CONVERT`  

0. Install the Postgres driver  
    `pip install psycopg2`  

0. Set python path:  
    `export PYTHONPATH=/mnt/code/xbrowse:/mnt/code/xbrowse-settings:$PYTHONPATH`  
  
0. Initialize the database. This django command creates the database xBrowse uses for storing users, project and other metatada.  
  `cd /mnt/code/xbrowse`  
  `python2.7 manage.py migrate`  

0. Load reference data - genes, population variation, etc.  
This will take ~20 minutes (a sequence of progress bars will show).  
  `python2.7 manage.py load_resources`  

0. Create superuser(s). It will ask you to create a username and password which you will then be able to use to login to the development website. This user will have access to all xBrowse projects on your development instance.  
  `python2.7 manage.py createsuperuser`  

Things are mostly set up now, but if you try to load the public DNS of this machine in a web browser - you actually won't be able to connect. One final hack is in order.  We need to loosen the machine's SELinux and firewall rules so it can accept public traffic:  

  `iptables -F && iptables -A FORWARD -j REJECT && /etc/init.d/iptables save`  

Now visit your public DNS again, and you should see the familiar xBrowse homepage.  

## Load Test Data  

However, this instance does not have any data loaded. We'll load a test project now.  

0. Initialize the 1kg example project:  
   `python2.7 manage.py add_project 1kg`  

0. Populate project with data from the test project directory:  
   `python2.7 manage.py load_project_dir 1kg /mnt/data/projects/1kg_project`  

0. To load the VCF data:  
   `python2.7 manage.py load_project 1kg`  

   This should take ~1 hour - it has to parse all the variants from the VCF file, annotate them, and load them into the variant database (annotation speed is the main bottleneck).  
