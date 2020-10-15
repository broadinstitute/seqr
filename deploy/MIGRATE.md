This README describes steps for migrating an older seqr instance.

1. Backup your current SQL database:

   ```
   pg_dump -U postgres seqrdb | gzip -c - > backup.gz
   ```

2. Download or clone the lastest seqr code from [https://github.com/broadinstitute/seqr](https://github.com/broadinstitute/seqr)

3. Run migrations:
   ```
   python -m manage makemigrations 
   python -m manage migrate 
   python -m manage loaddata variant_tag_types // This will fail if it has been run before, and that is okay
   python -m manage loaddata variant_searches // This will fail if it has been run before, and that is okay
   python -m manage reload_saved_variant_json
   ```
    
4. Update gene-level reference datasets:
    ```
    psql -U postgres postgres -c "drop database reference_data_db"
    psql -U postgres postgres -c "create database reference_data_db"
    REFERENCE_DATA_BACKUP_FILE=gene_reference_data_backup.gz
    wget -N https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz -O ${REFERENCE_DATA_BACKUP_FILE}
    psql -U postgres reference_data_db <  <(gunzip -c ${REFERENCE_DATA_BACKUP_FILE})
    rm ${REFERENCE_DATA_BACKUP_FILE}
    ```
