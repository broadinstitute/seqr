The "custom reference populations" feature allows allele frequencies (AFs) to be loaded for datasets other than 1kg and ExAC.
There are several steps involved in creating and loading a new reference population. 
First a name, id, and source file for the new reference population is registered. AFs can be loaded from either a sites VCF or .tsv file.
Then the AF data is loaded into the seqr database. Then, a frequency filter for this population can then be added to seqr Variant Search 
on a project-by-project basis.

1. Register the new population
```
python2.7 manage.py create_custom_population --name "My Custom Population" --file_type 'sites_vcf_with_counts' --file_path /path/to/my_sites.vcf.gz  my-custom-population-id

NOTE:
   --name sets the label that will be shown above the filter slider in seqr Variant Search in projects to which this population will be added
   --file_type can be:  "vcf", "sites_vcf", "sites_vcf_with_counts", "counts_file", "tsv_file". The different options allow AFs to be loaded from the VCF's AC, AN counts, or directly from the AF field if present. See population_frequency_store.py for details.
```
  
2. Load the data
```
python2.7 -u -m manage load_custom_populations my-custom-population-id

or to load the AFs from custom INFO field keys:

python2.7 -u -m manage load_custom_populations --AC-key AC_POPMAX --AN-key AN_POPMAX   my-custom-population-id

```

3. Add an AF filter for this population to a specific project
```
python manage.py add_custom_population_to_project  seqr-project-id  my-custom-population-id
```
