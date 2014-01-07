Getting Started
===============

This is a quick guide to using xBrowse at the command line.

Installation
------------

I haven't created a formal python package yet, so for now installation instructions are pretty rough.
Ask me if any questions...

- Create and activate a virutalenv:

    virtualenv my_env
    cd my_env
    source bin/activate

- Clone this repository

    git clone https://github.com/brettpthomas/xbrowse

- Install dependencies:

    pip install -r xbrowse/requirements.txt

- Run the tests

    # only unit tests for now; more coming
    python xbrowse/test/unit.py

Getting Started
---------------

For now, we'll only consider the canonical xBrowse use case: searching for a Mendelian disease mutation.
As an example, download the following VCF:

This VCF file contains exome sequencing data from the 1000 Genomes CEU Trio.
This trio consists of a xxx.
It includes NA12878, whose genome has been sequenced to high quality on a variety of platforms as a measure of quality control.

However, the child in this trio of course does not have a Mendelian disease,
so we added a few known disease mutations to that VCF file to make this tutorial more interesting.

### Setting Up

That VCF file only contains variants - but in order to prioritize causal variants,
we also need some additional reference data.

All the data needed by xbrowse is packaged into a reference data directory.
Download and unzip the following file: xxx

It doesn't matter where you put that folder, but you still need to tell xBrowse where to find it.
This is one of many installation-specific settings that are available to
Open up `settings.py` and set the value of `REFERENCE_DATA_DIR` to the path of the folder you just unzipped.

settings.py should have a line that looks something like this:

    REFERENCE_DATA_DIR = "/home/bt/xbrowse_reference_data"

(trailing slash is optional)

Now run the following command:

    python client/check_installation.py

You should see some friendly output indicating that your installation of xBrowse is ready to go.

### Running a Search

W

    # search for recessive variants in a family
    python xbrowse/scripts/variant_search.py