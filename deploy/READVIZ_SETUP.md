
If you have alignment files in **.bam** or **.cram** format for the sample(s) in your VCF, seqr allows read data 
for individual variants to be viewed in the browser using [IGV.js](https://github.com/igvteam/igv.js/wiki).

The steps to enable this feature depend on whether it's easier to place your read data files on the local 
filesystem of the machine that's running your seqr server, or on a remote machine (either on-prem or in the cloud).   

   
### Choosing local vs. remote hosting of read data

If putting read data files on the local filesystem is possible (either via copying or mounting the data), it makes setup and maintenance easier (see steps below). 

Often this won't be an option for on-prem installations where the large file system that contains the read data is isolated from 
web-facing machines due to security or other considerations. 
In that case, a separate http (or https) server must be run on machine that does have direct access to the read files, 
and the network must allow http requests from the seqr application server to this other http server.


### Option 1: Local files
 
As described above, if your read files are located on the machine that's running the seqr application server, these steps will enable
viewing this read data through IGV.js:

1) create a tab-delimited text file - let's call it `bam_paths.tsv` - with these 2 columns (and no header line):
    
   **individual_id**  - the seqr individual id     
   **bam_path** - this should be the path of the .bam file on the local filesystem. Each .bam file must also have a .bam.bai index file next to it. 
   The .bam path can be an absolute path (like `/path/to/file.bam`), or a relative path (like `some-dir/file.bam`) - relative to the `READ_VIZ_BAM_PATH` defined in `local_settings.py`. Relative paths can be useful if all your .bams are in some top-level directory which might change later.        
   
2) Run `python manage.py set_bam_paths <project_id>  bam_paths.tsv` to point seqr to these files. 


[TODO: docs for .cram format]

### Option 2: Remote files

[TODO: docs for .bam or .cram files on a remote server]

 



