This README describes steps for migrating an older xBrowse or seqr instance.

1. Backup your current SQL database:

   ```
   pg_dump -U postgres seqrdb | gzip -c - > backup.gz
   ```

2. Download or clone the lastest seqr code from [https://github.com/macarthur-lab/seqr](https://github.com/macarthur-lab/seqr)

3. Run migrations:
   ```
   python2.7 -m manage makemigrations 
   python2.7 -m manage migrate 
   python2.7 -m manage loaddata variant_tag_types // This will fail if it has been run before, and that is okay
   python2.7 -m manage loaddata variant_searches // This will fail if it has been run before, and that is okay
   ```
   
4. If you were previously on a version of seqr that used mongo instead of elasticsearch to store variant data, 
load new datasets into elasticsearch using the hail-based pipelines described in the main README. 
If you were previously using elasticsearch, run:
    ```
    python2.7 -m manage reload_saved_variant_json
    ```
    
5. Update gene-level reference datasets:
    ```
    psql -U postgres postgres -c "drop database reference_data_db"
    psql -U postgres postgres -c "create database reference_data_db"
    REFERENCE_DATA_BACKUP_FILE=gene_reference_data_backup.gz
    wget -N https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz -O ${REFERENCE_DATA_BACKUP_FILE}
    psql -U postgres reference_data_db <  <(gunzip -c ${REFERENCE_DATA_BACKUP_FILE})
    rm ${REFERENCE_DATA_BACKUP_FILE}
    ```
    
6. If after relaunching seqr you do not see any projects on the main page, check if your data is available on the 
deprecated pages (http://localhost:8000/projects). If so run the following to transfer to the new pages:
    ```
    python2.7 -m manage update_projects_in_new_schema
    python2.7 -m manage transfer_gene_lists
    python2.7 -m manage transfer_gene_notes
    ```