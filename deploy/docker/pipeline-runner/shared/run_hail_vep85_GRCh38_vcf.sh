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
  --fasta /vep/homo_sapiens/85_GRCh38/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz \
  --minimal \
  --assembly GRCh38 \
  --plugin LoF,human_ancestor_fa:/vep/loftee_data_grch38/loftee_data/human_ancestor.fa.gz,filter_position:0.05,min_intron_size:15 \
  -o STDOUT
