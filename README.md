
xBrowse
=======

xBrowse is a software package for working with next generation sequencing data,
specifically in the context of studying rare genetic diseases.

This package contains the analysis code that powers the [xBrowse web app](http://atgu.mgh.harvard.edu/xbrowse).
You can use this code to run the xBrowse analyses on the command line, if websites aren't your thing.

We will soon be adding all of the website code to this repository as well -
we are running through some security audits first.
Our goal is to make it easy for you to set up a private instance of xBrowse on your own infrastructure.

**Please Note:** This package is in active development, and the API is extremely unstable -
actually volatile is probably a better description. We suggest you contact us if you want to build on this repo.

## Installation Instructions

### Installation

This will depend on how you are deploying xBrowse.
If you are working in the Vagrant box (xbrowse-laptop), then this is done for you.
Server installations will vary.

### Initialization

Before you can actually run xBrowse, you'll need to initialize some resources.
The first is the Django server database. Do this with:

    ./manage.py syncdb --all

This is a Django command that creates the database xBrowse uses to store users and other website data.
It will ask you to create a username and password for the "superuser"; this is up to you.

### Add a project

Now we'll add a project to xBrowse, so you actually have some data to look at.
Download and extract the following tarball:

    wget ftp://atguftp.mgh.harvard.edu/1kg_project.tar.gz
    tar -xzf 1kg_project.tar.gz

That creates a directory `1kg_project`, which is an xBrowse *Project Directory* -
a directory that stores all of the data and configuration for a single xBrowse project.

We can load that project directory into xBrowse with the following set of commands.

Create a project named 1kg:

    ./manage.py add_project 1kg

Initialize the new project with data from the project directory:

    ./manage.py load_project_dir 1kg /path/to/1kg_project

Now the project has been initialized, but not actually loaded into the database. One final step:

    ./manage.py load_project 1kg

This will take ~an hour. When it's finished, the project will be available on the xBrowse homepage.

## Tests

After you've loaded the 1000 Genomes test project, you can run integration tests with the following command:

    python functional_tests.py

These tests assume that the `1kg` project above has been loaded - they run
a bunch of browser simulations to make sure that the correct search results are returned.