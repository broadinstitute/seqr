This README describes steps for migrating an older xBrowse instance. 

seqr is still not ready for an official major release, but the database schema and loading pipelines have 
stabilized so anyone that wants migrate an older xBrowse instance to the current seqr instance can do so by 
following these steps:

1. Backup your current SQL database:

   ```
   pg_dump -U postgres seqrdb | gzip -c - > backup.gz
   ```

2. Download or clone the lastest seqr code from [https://github.com/macarthur-lab/seqr](https://github.com/macarthur-lab/seqr)

3. Run migrations:

   ```
   python2.7 -m manage makemigrations   # this is just a sanity check and shouldn't create any new migrations
   python2.7 -m manage migrate 
   ```

4. Copy existing data to the new database tables:
    ```
    python2.7 -m manage transfer_gene_lists
    python2.7 -m manage update_projects_in_new_schema
    python2.7 -m manage reload_saved_variant_json
    ```
    
5. Update gene-level reference datasets:
    ```
    python2.7 -m manage update_all_reference_data --omim-key $(cat deploy/secrets/minikube/seqr/omim_key)
    ```
6. Load new datasets into elasticsearch using the hail-based pipelines described in the main README.