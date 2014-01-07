HIGHVARIABILITY_GENES_FILE = "/Users/bt/xbrowse/referencedata/bad_genes.ensembl.txt"

REFERENCE_POPULATIONS = [
    {
        'name': 'atgu_controls',
        'file_type': 'vcf',
        'file_path': '/Users/bt/xbrowse/referencedata/annotated_broad_cc.vcf',
    },
    {
        'name': 'g1k_all',
        'file_type': 'sites_vcf',
        'file_path': '/Users/bt/xbrowse/referencedata/ALL.wgs.integrated_phase1_v3.20101123.snps_indels_sv.sites.vcf',
        'vcf_info_key': 'AF',
    },
    {
        'name': 'esp_all',
        'file_type': 'esp_counts_dir',
        'dir_path': '/Users/bt/xbrowse/referencedata/esp_text_files/',
        'counts_key': 'esp_all',
    },
    {
        'name': 'esp_ea',
        'file_type': 'esp_counts_dir',
        'dir_path': '/Users/bt/xbrowse/referencedata/esp_text_files/',
        'counts_key': 'esp_ea',
    },
    {
        'name': 'esp_aa',
        'file_type': 'esp_counts_dir',
        'dir_path': '/Users/bt/xbrowse/referencedata/esp_text_files/',
        'counts_key': 'esp_aa',
    },
]
