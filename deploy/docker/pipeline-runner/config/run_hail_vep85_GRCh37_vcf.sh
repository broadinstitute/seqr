#!/bin/bash

file=$1

export PERL5LIB=/vep/loftee

perl /vep/variant_effect_predictor/variant_effect_predictor.pl \
-i $file \
--format vcf \
  --vcf \
  --everything \
  --allele_number \
  --no_stats \
  --cache --offline \
  --dir /vep \
  --fasta /vep/homo_sapiens/85_GRCh37/Homo_sapiens.GRCh37.75.dna.primary_assembly.fa \
  --minimal \
  --assembly GRCh37 \
  --plugin LoF,human_ancestor_fa:/vep/loftee_data_grch37/loftee_data/human_ancestor.fa.gz,filter_position:0.05,min_intron_size:15 \
  -o STDOUT
