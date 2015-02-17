
xBrowse: Amazon Web Services
====================================

The steps below describe how to set up a fully isolated instance of xBrowse on Amazon Web Services.
We begin with vanilla CentOS 6.5 virtual machine,
and provision an xBrowse server can be accessed over a public URL.

Although these steps are specific to AWS and CentOS 6,
they map closely to the steps you'd take to install xBrowse on other systems.
For example, this is a very similar process to how we administer xBrowse at the Broad Institute,
with a few modifications to accommodate specifics to our internal infrastructure.

Note that we don't maintain any prebuilt AMIs at this time,
though you could use the result of this tutorial to package AMIs for internal use.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [xBrowse: Amazon Web Services](#xbrowse-amazon-web-services)
  - [Prerequisite: AWS Account](#prerequisite-aws-account)
  - [Create the Virtual Machine](#create-the-virtual-machine)
  - [Prepare the VM](#prepare-the-vm)
  - [Install xBrowse](#install-xbrowse)
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
(Note that this AMI is only available in the US East region, `us-east-1`).
Use instance type `m3.medium`, or something more powerful.

0. Create an EBS Volume with at least 50 GB storage. This is where all of the xBrowse data and database files will go.

0. Attach and mount the EBS volume to the VM. In this document, we assume that the volume is mounted to `/mnt`.

At this point, you should be able to log into the machine:

    ssh -i /path/to/private/key root@url.of.machine

Make sure that the mountpoint is correctly set up - it should look something like this:

    $ df -H
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/xvde       8.5G  682M  7.4G   9% /
    tmpfs           2.0G     0  2.0G   0% /dev/shm
    /dev/xvdl        53G  189M   50G   1% /mnt

## Provisioning the machine

A bulk of the provisioning in xBrowse is performed by Puppet, but a few steps are run manually.
Log into the machine and do the following:

0. Update Yum
    `sudo yum -y update`

0. Install git and wget
    `sudo yum install git wget -y`

0. Install Puppet
    `sudo rpm -Uvh http://yum.puppetlabs.com/el/6/products/i386/puppetlabs-release-6-7.noarch.rpm`
    `sudo yum -y -q install puppet`

0. We need to loosen the machine's SELinux and firewall rules so it can accept public traffic:
    `yum install policycoreutils-python -y`
    `cat /var/log/audit/audit.log | grep nginx | grep denied | audit2allow -M mynginx`
    `iptables -F && iptables -A FORWARD -j REJECT && /etc/init.d/iptables save`

0. Create subdirectories:
   `cd /mnt`
   `mkdir code data mongodb`

0. Download the xbrowse data tarball (411Mb). It contains reference data + an example project based on 1000 genomes data.
   `cd /mnt/data`
   `wget ftp://atguftp.mgh.harvard.edu/xbrowse-resource-bundle.tar.gz`
   `tar -xzf xbrowse-resource-bundle.tar.gz`

0. Run Puppet to provision this machine for xBrowse. This takes a while (~2 hours) and performs a bulk of the provisioning.

    puppet apply /mnt/code/xbrowse/deploy/ec2/ec2_provision.pp --modulepath=/mnt/code/xbrowse/deploy/puppet/modules

0. Download and install VEP. It's used by xBrowse to annotate variants.
   `cd /mnt`
   `wget https://github.com/Ensembl/ensembl-tools/archive/release/78.zip`
   `unzip 78.zip`
   `mv ensembl-tools-release-78/scripts/variant_effect_predictor .`
   `rm -rf 78.zip ensembl-tools-release-78`
   `cd variant_effect_predictor`
   `perl INSTALL.pl --AUTO acf --CACHEDIR ../vep_cache_dir --SPECIES homo_sapiens --ASSEMBLY  GRCh37 --CONVERT`

0. Install the Postgres driver
    `pip install psycopg2`

0. Initialize the database. This django command creates the database xBrowse uses for storing users, project and other metatada.
   `cd /mnt/code/xbrowse`
   `python2.7 /manage.py migrate`

0. Load reference data - genes, population variation, etc. This will take ~20 minutes (a sequence of progress bars will show).
   `python2.7 manage.py load_resources`

0. Create superuser(s). This user will have access to all xBrowse projects on your development instance.
   `python2.7 manage.py createsuperuser   # it will ask you to create a username and password`

0. Create a Site TKTKTK


Now visit your public DNS again, and you should see the familiar xBrowse homepage.

## Load Test Data

No data has been loaded yet.



puppet apply ${XBROWSE_INSTALL_DIR}/code/xbrowse/deploy/ec2/ec2_provision.pp --modulepath=${XBROWSE_INSTALL_DIR}/code/xbrowse/deploy/puppet/modules



Notes

- I left out the XBROWSE_INSTALL_DIR stuff because it needs to be hardcoded re: puppet

- I removed the