#!/usr/bin/env bash

set -eux

REFERENCE_GENOME=$1
VEP_REFERENCE_DATASETS_DIR=${VEP_REFERENCE_DATASETS_DIR:-/var/seqr/vep-reference-data}
DEFAULT_REFERENCE_DATASETS_DIR="gs://seqr-reference-data"
if [[ -n "${REFERENCE_DATASETS_DIR:-}" && "$REFERENCE_DATASETS_DIR" == gs://* ]]; then
  echo "Using overridden GCS path: $REFERENCE_DATASETS_DIR"
else
  REFERENCE_DATASETS_DIR="$DEFAULT_REFERENCE_DATASETS_DIR"
  echo "Using default GCS path: $REFERENCE_DATASETS_DIR"
fi

case $REFERENCE_GENOME in
  GRCh38)
    VEP_REFERENCE_DATA_FILES=(
        "$REFERENCE_DATASETS_DIR/vep_data/loftee-beta/GRCh38.tar.gz"

        # Raw data files copied from the bucket (https://console.cloud.google.com/storage/browser/dm_alphamissense;tab=objects?prefix=&forceOnObjectsSortingFiltering=false)
        # tabix -s 1 -b 2 -e 2 -f -S 1 AlphaMissense_hg38.tsv.gz
        "$REFERENCE_DATASETS_DIR/vep/GRCh38/AlphaMissense_hg38.tsv.*"

        # Generated with:
        # curl -O ftp://ftp.ensembl.org/pub/release-110/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz > Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
        # gzip -d Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
        # bgzip Homo_sapiens.GRCh38.dna.primary_assembly.fa
        # samtools faidx Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
        "$REFERENCE_DATASETS_DIR/vep/GRCh38/Homo_sapiens.GRCh38.dna.primary_assembly.fa.*"

        # Copied from ftp://ftp.ensembl.org/pub/release-110/variation/indexed_vep_cache/homo_sapiens_vep_110_GRCh38.tar.gz
        "$REFERENCE_DATASETS_DIR/vep/GRCh38/homo_sapiens_vep_110_GRCh38.tar.gz"

        # Copied from the UTRAnnotator repo (https://github.com/ImperialCardioGenetics/UTRannotator/tree/master)
        "$REFERENCE_DATASETS_DIR/vep/GRCh38/uORF_5UTR_GRCh38_PUBLIC.txt"

        "$REFERENCE_DATASETS_DIR/vep/GRCh38/vep-GRCh38.json"
    )
    ;;
  GRCh37)
    VEP_REFERENCE_DATA_FILES=(
        "$REFERENCE_DATASETS_DIR/vep_data/loftee-beta/GRCh37.tar.gz"
        "$REFERENCE_DATASETS_DIR/vep/GRCh37/homo_sapiens_vep_110_GRCh37.tar.gz"
        "$REFERENCE_DATASETS_DIR/vep/GRCh37/Homo_sapiens.GRCh37.dna.primary_assembly.fa.*"
        "$REFERENCE_DATASETS_DIR/vep/GRCh37/vep-GRCh37.json"
    )
    ;;
   *)
    echo "Invalid reference genome $REFERENCE_GENOME, should be GRCh37 or GRCh38"
    exit 1
esac

if [ -f "$VEP_REFERENCE_DATASETS_DIR"/"$REFERENCE_GENOME"/_SUCCESS ]; then
   echo "Skipping download because already successful"
   exit 0;
fi

mkdir -p "$VEP_REFERENCE_DATASETS_DIR"/"$REFERENCE_GENOME";
rm -rf "${VEP_REFERENCE_DATASETS_DIR:?}"/"${REFERENCE_GENOME:?}"/*;

for vep_reference_data_file in "${VEP_REFERENCE_DATA_FILES[@]}"; do
    if  [[ $vep_reference_data_file == *.tar.gz ]]; then
        echo "Downloading and extracting" "$vep_reference_data_file";
        gsutil cat "$vep_reference_data_file" | tar -xzf - -C "$VEP_REFERENCE_DATASETS_DIR"/"$REFERENCE_GENOME"/ &
    else
        echo "Downloading" "$vep_reference_data_file";
        gsutil cp "$vep_reference_data_file" "$VEP_REFERENCE_DATASETS_DIR"/"$REFERENCE_GENOME"/ &
    fi
done;
wait
touch "$VEP_REFERENCE_DATASETS_DIR"/"$REFERENCE_GENOME"/_SUCCESS
