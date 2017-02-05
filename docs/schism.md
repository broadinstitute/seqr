Searching for Causal Genomic Breakpoints
========================================

Schism is a system for identifying a unique or extremely rare genomic breakpoints in 
high throughput sequencing (HTS) data. These breakpoints often represent structural variants
such as large deletions or duplications that can cause disease but are difficult to identify
in short read genomic data.

## Running Schism on a BAM file

Schism can be run on a single gene using a command line such as the following:

```
findbp -region DMD -maxsc 5 -mindp 3 -bam my_sample.bam > breakpoints.tsv
```

This will find breakpoints and compare them to databases placed in the Schism control
database directory. You can explicitly specify a control database, or build one if you don't have
one using the `builddb` command.

More typically one may run Schism on regions of significant interest, such as a predefined gene list.
Typically, some padding would be provided to capture breakpoints that occur outside a gene but which
overlap with the gene. It is also useful to provide a reference (which often can be found automatically using the `-ref auto` option):

```
findbp -ref auto  -mindp  5  -pad 20000  -genelist master_gene_list.txt  -maxsc 5 -bam my_sample.bam \
  > breakpoints.tsv
```

## Loading Schism Data

Once the TSV file containing breakpoints has been produced, it can be loaded into Schism. To 
do this, create a project directory as described in [Project Directory](project_directory.md).
Inside the project's YAML file, include a reference to the breakpoint files using the format in 
the example below:

```
project_id: 'my_project'

project_name: 'My Great Project'

sample_id_list: 'all_samples.txt'

ped_files:
  - 'sample_data/my_project.ped'

breakpoint_files:
  - 'sample_data/breakpoints.tsv'
```

Note that the PED file and sample file is necessary as well as the breakpoint file. These 
should be created as normal for Seqr projects.

Once the files are ready, add the project:

```
./manage.py add_project my_project 'My Great Project'
```

_Note_: these steps are common to loading variants; if you're loading variants for the samples
too you should place those into the project file as well.

Then load the project directory as per normal:

```
./manage.py load_project_dir  my_project ../../data/projects/my_project
```

Then load the project data:

```
./manage.py load_project my_project
```

## Making BAM Files Viewable

It is particularly important to look at alignments for structural variants. By default, Seqr will load
the location of the breakpoint in IGV when you click an IGV link, but not the correct BAM file for the
sample. To make the correct breakpoint be loaded, use the set_bam_paths command. To do this you need
a tab separated file containing samples and bam paths. Here is an example of how to create that
using GroovyNGS Utils:

```groovy
base="/path/to/my/bam/files"
new File("sample_bams.tsv").text = base.listFiles().grep { 
 it.name.endsWith(".bam") 
}.collect { 
  [ new SAM(it).samples[0], it.absolutePath ].join("\t") 
} .join("\n") + "\n"
```

Next, make sure that the READVIZ path is set in your settings.py - eg:

```
READ_VIZ_BAM_PATH = "https://iwww.broadinstitute.org/igvdata"
```

Then load the BAM file paths into Seqr like so:

```
./manage.py set_bam_paths my_project ../../data/projects/my_project/sample_data/sample_bams.tsv 
```



