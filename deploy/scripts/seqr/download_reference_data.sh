set -x

mkdir -p data data/reference_data data/projects

cd data/reference_data

#wget -c -N http://seqr.broadinstitute.org/static/bundle/seqr-resource-bundle.tar.gz && tar -xzf seqr-resource-bundle.tar.gz

# wget -c -N http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz &
# wget -c -N http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz &


wget -c -N http://seqr.broadinstitute.org/static/bundle/1kg_project.tar.gz && tar -xzf 1kg_project.tar.gz

