
If you have alignment files in **.bam** or **.cram** format for the sample(s) in your VCF, seqr allows read data 
for individual variants to be viewed in the browser using [IGV.js](https://github.com/igvteam/igv.js/wiki).

If your read files are located on the machine that's running the seqr application server, these steps will enable
viewing this read data through IGV.js:

1) When running seqr using docker-compose (as [described here](https://github.com/broadinstitute/seqr/blob/master/deploy/LOCAL_INSTALL.md)), 
place the bam/cram and index files in the `./data/readviz/` sub-directory that was created under the directory containing
the docker-compose.yml file. When you start seqr, docker-compose will mount the `./data/readviz/` directory to a `/readviz`
top-level directory inside the seqr container.

2) Create a tab-delimited or comma-delimited text file - let's call it `bam_paths.tsv` - with these 2 columns (and no 
header line):
    
   **individual_id**  - the seqr individual id
   
   **bam_or_cram_path** - the *absolute path* of the .bam or .cram file on the local filesystem where the seqr 
    gunicorn server is running (eg. `/readviz/dir/file.bam`).  Each bam/cram file must also have an index file next 
    to it (.bam.bai or .cam.crai). 
   
   
3) Go to the project page in seqr and click "Edit Datasets" and then click on the "Add BAM/CRAM Paths" tab in the 
resulting pop up. Upload the file from step 1 and click the "Submit" button
