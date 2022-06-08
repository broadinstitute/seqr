#!/usr/bin/env bash

set -x -e

BUILD_VERSION=$1

# download VEP cache
mkdir -p /vep_data/homo_sapiens
cd /vep_data
CACHE_FILE=homo_sapiens_vep_99_GRCh${BUILD_VERSION}.tar.gz
curl -LO "http://ftp.ensembl.org/pub/release-99/variation/indexed_vep_cache/${CACHE_FILE}"
tar xzf "${CACHE_FILE}"
rm "${CACHE_FILE}"

if [[ "${BUILD_VERSION}" == "38" ]]; then
    cd /vep_data/homo_sapiens
    curl -O http://ftp.ensembl.org/pub/release-99/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
    gzip -d Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
    bgzip Homo_sapiens.GRCh38.dna.primary_assembly.fa
fi

# download loftee reference data
mkdir -p "/vep_data/loftee_data/GRCh${BUILD_VERSION}"
cd "/vep_data/loftee_data/GRCh${BUILD_VERSION}"
LOFTEE_FILE=GRCh${BUILD_VERSION}.tar
gsutil cp "gs://seqr-reference-data/vep_data/loftee-beta/${LOFTEE_FILE}" .
tar xf "${LOFTEE_FILE}"
rm "${LOFTEE_FILE}"

# download seqr reference data
REF_DATA_HT=combined_reference_data_grch${BUILD_VERSION}.ht
CLINVAR_HT=clinvar.GRCh${BUILD_VERSION}.ht
mkdir -p "/seqr-reference-data/GRCh${BUILD_VERSION}/${REF_DATA_HT}"
mkdir -p "/seqr-reference-data/GRCh${BUILD_VERSION}/${CLINVAR_HT}"
cd "/seqr-reference-data/GRCh${BUILD_VERSION}"
gsutil -m rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/all_reference_data/${REF_DATA_HT}" "./${REF_DATA_HT}"
gsutil -m rsync -r "gs://seqr-reference-data/GRCh${BUILD_VERSION}/clinvar/${CLINVAR_HT}" "./${CLINVAR_HT}"
