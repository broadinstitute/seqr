#!/usr/bin/env bash

set +x
set +x

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi

echo
echo "==== Installing seqr ===="
echo
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    :

elif [ $PLATFORM = "centos" ]; then

    sudo yum install -y \
        cairo \
        cairo-devel \
        glib2 \
        glib2-devel \
        pango \
        pango-devel \
        gtk2

    sudo apt-get update \
        && curl --silent --location https://rpm.nodesource.com/setup_8.x | sudo bash - \
        && sudo yum -y install nodejs

elif [ $PLATFORM = "ubuntu" ]; then

    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    sudo apt-get install -y \
        perl \
        build-essential \
        libcairo2-dev \
        libglib2.0-bin \
        libglib2.0-0 \
        libgtk2.0-dev \
        libpango1.0-dev

    sudo apt-get update \
        && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
        && sudo apt-get install -y \
              nodejs

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;

wget -nv https://raw.github.com/miyagawa/cpanminus/master/cpanm -O cpanm \
    && chmod +x ./cpanm \
    && sudo ./cpanm --notest \
        Cairo \
        DBI \
        Gtk2 \
        Tk \
        Sort::Naturally

cd ${SEQR_DIR}/
mkdir seqr_settings
cp deploy/docker/seqr/config/*.py seqr_settings/

# install python dependencies
sudo $(which pip) install --upgrade --ignore-installed -r requirements.txt

# init seqr db
psql -U postgres postgres -c "create database seqrdb"

# init django
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input
python -u manage.py loaddata variant_tag_types
python -u manage.py loaddata variant_searches

# download and restore gene reference data
for table_name in \
    reference_data_humanphenotypeontology reference_data_mgi reference_data_omim reference_data_primateai reference_data_transcriptinfo \
    reference_data_dbnsfpgene reference_data_geneconstraint reference_data_geneexpression reference_data_geneinfo; do

    psql -U postgres seqrdb -c "DROP TABLE ${table_name}"
done

REFERENCE_DATA_BACKUP_FILE=gene_reference_data_backup.gz
wget -N https://storage.googleapis.com/seqr-reference-data/gene_reference_data_backup.gz -O ${REFERENCE_DATA_BACKUP_FILE}
rm ${REFERENCE_DATA_BACKUP_FILE}

# start gunicorn server
GUNICORN_WORKER_THREADS=4

echo 'cd '${SEQR_DIR}'/seqr_settings

LOG_FILE=$(pwd)/gunicorn.log
nohup gunicorn -w '${GUNICORN_WORKER_THREADS}' -c gunicorn_config.py wsgi:application --bind 0.0.0.0:8000 >& ${LOG_FILE} &
echo "gunicorn started in background. See ${LOG_FILE}"
' > start_server.sh
chmod 777 ./start_server.sh

./start_server.sh

set +x