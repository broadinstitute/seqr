**Testing**  

To run server-side django tests:

```
python2.7 -Wmodule -u manage.py test -p '*_tests.py' -v 2
```


To run client-side tests:

```
cd ui
npm test
```



**Refactoring**

seqr is currently going through a transition to an updated tech stack and undergoing major refactoring. 
This will allow us to solve some long-standing issues and feature requests, make the code base more 
flexible and easier for multiple developers to modify, and incorporate more best-practices in terms of 
design and testing.    

For the user interface (UI), we are replacing *Django server-side templates*, *Backbone.js*, *Bootstrap* 
with *React.js+JSX*, *Redux*, *Semantic UI* and switching to using webpack + Babel for building the 
client-side code. Among other benefits, this will allow us to use the latest javascript build tools for 
packaging, optimizing, linting, etc., as well as code using the new ES6 language features.    
On the server-side, we are updating core data models and overhauling the APIs to update the 
overall design to current needs. As part of this update we will transition from python v2 to python v3.

*New directory structure:*
1. the top-level /seqr directory is a new Django app that contains the new seqr core (including 
the updated database schema in *models.py* as well as the url endpoints for any new or refactored APIs)
2. the top-level /ui directory contains all files for the new react.js-based UI
3. the top-level /reference_data directory is another new Django app that contains refactored 
django commands and scripts for loading reference datasets such as OMIM, clinvar, HPO, gencode, etc. 


**Backing Up, Restoring Existing Data**

To export all data from an existing postgres database in your local seqr installation, run:
```
pg_dump -U postgres seqrdb | gzip -c - > seqrdb_backup.txt.gz
pg_dump -U postgres xwiki | gzip -c - > xwiki_backup.txt.gz
```

If restoring to a clean postgres database, you must first re-create the two user roles used by seqr 
and phenotips. This can be done by running the following commands in the postgres shell (psql):

```
create user postgres CREATEDB;
create user xwiki CREATEDB;
```
To restore the backed-up data, run:

```
# restore seqr database
psql -U postgres template1 < <(echo create database seqrdb)
psql seqrdb < <(gunzip -c seqrdb_backup_*.txt.gz)

# restore phenotips database
psql -U xwiki template1 < <(echo create database xwiki)
psql xwiki < <(gunzip -c xwiki_backup_*.txt.gz)

```


**Migrating Existing Data to the New Database Schema and UI**

Running the following 2 commands will copy metadata from the original database tables that are used by the current UI into the new tables that are used by the new API and React.js-based UI:

```
/usr/local/bin/python2.7 -m manage transfer_gene_lists
/usr/local/bin/python2.7 -m manage update_projects_in_new_schema
```

