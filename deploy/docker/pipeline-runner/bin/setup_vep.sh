#!/usr/bin/env bash

set -x -e

# download VEP cache
WORKDIR /root/.vep
RUN curl -LO http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/homo_sapiens_vep_99_GRCh38.tar.gz
#RUN curl -LO http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/homo_sapiens_vep_99_GRCh37.tar.gz
 #| tar xzf - &

# download loftee reference data
WORKDIR /vep_data/loftee_data
RUN gsutil -m cp gs://seqr-reference-data/vep_data/loftee-beta/GRCh37.tar . | tar x
# | tar xf  - &
#RUN gsutil -m cp gs://seqr-reference-data/vep_data/loftee-beta/GRCh38.tar