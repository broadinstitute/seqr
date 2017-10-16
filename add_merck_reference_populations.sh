for p in Merck-Phase5-WES-CCHMC NIAMS_Phase6_WES Snapper_Phase6_WES Geha_Phase6_WES;
do
    for i in merck-wgs-3793 merck-pcr-free-wgs-144 merck_48k_wgs merck_730_pcr_free gleeson_gme gnomad-exomes gnomad-genomes; 
    do 
	echo $p   $i 
	python2.7 manage.py add_custom_population_to_project $p $i 
    done;
done;
