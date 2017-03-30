FROM python:2.7.11

MAINTAINER MacArthur Lab


RUN git clone -q https://github.com/macarthur-lab/seqr

# init local config files
WORKDIR seqr

RUN pip install --upgrade pip gunicorn \
    && pip install --upgrade -r requirements.txt

RUN apt-get update \
    && apt-get install -y emacs

RUN cp deploy/scripts/gunicorn/conf/* .

COPY config/*.py ./

EXPOSE 8000

ENTRYPOINT ["gunicorn", "-c", "gunicorn_config.py", "wsgi:application", "--timeout", "3600"]



#mkdir -p data data/reference_data data/projects

#cd data/reference_data

#wget -c -N http://seqr.broadinstitute.org/static/bundle/seqr-resource-bundle.tar.gz && tar -xzf seqr-resource-bundle.tar.gz

# wget -c -N http://seqr.broadinstitute.org/static/bundle/ExAC.r0.3.sites.vep.popmax.clinvar.vcf.gz &
# wget -c -N http://seqr.broadinstitute.org/static/bundle/ALL.wgs.phase3_shapeit2_mvncall_integrated_v5a.20130502.sites.decomposed.with_popmax.vcf.gz &

#wget -c -N http://seqr.broadinstitute.org/static/bundle/1kg_project.tar.gz && tar -xzf 1kg_project.tar.gz

#cd ${INSTALL_DIR}/seqr

#python manage.py makemigrations
#python manage.py migrate

#python manage.py collectstatic --noinput

#curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python;

#sudo PATH=postgres/pgsql/bin/:$PATH  `which pip` install --upgrade -r seqr/requirements.txt;

#cd seqr
#python manage.py load_resources

#cd /local/software/seqr

#python manage.py transfer_gene_lists
#python manage.py update_human_phenotype_ontology
#python manage.py transfer_projects --dont-connect-to-phenotips
