cd /local/software/seqr

#python manage.py transfer_gene_lists
#python manage.py update_human_phenotype_ontology
python manage.py transfer_projects --dont-connect-to-phenotips
