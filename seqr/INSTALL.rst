Draft of steps for installing the new seqr UI:

- Postgres
- mongodb
- running tests


python manage.py migrate reference_data
python manage.py migrate seqr

python manage.py update_human_phenotype_ontology

python manage.py transfer_gene_lists
python manage.py transfer_projects



--------------------------------------------

npm