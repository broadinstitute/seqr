If you have alignment files in **.bam** or **.cram** format for the sample(s) in your VCF, seqr allows read data 
for individual variants to be viewed in the browser using [IGV.js](https://github.com/igvteam/igv.js/wiki), 
which canbe enabled with the following steps:

1) Place the bam/cram and index files inside the `/var/seqr/seqr-static-media` directory

1) Create a tab-delimited or comma-delimited text file - let's call it `bam_paths.tsv` - with these 2 columns (and no 
header line):
    
   **individual_id**  - the seqr individual id
   
   **bam_or_cram_path** - the *absolute path* of the .bam or .cram file on the local filesystem where the seqr 
    gunicorn server is running (eg. `/readviz/dir/file.bam`).  Each bam/cram file must also have an index file next 
    to it (.bam.bai or .cam.crai). 
   
1) Go to the project page in seqr and click "Edit Datasets" and then click on the "Add BAM/CRAM Paths" tab in the 
resulting pop up. Upload the file from step 1 and click the "Submit" button
