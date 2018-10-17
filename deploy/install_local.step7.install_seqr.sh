#!/usr/bin/env bash

echo "==== Installing seqr ===="
set -x

if [ -z "$PLATFORM" ]; then

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

    sudo wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O cpanm \
        && chmod +x ./cpanm \
        && ./cpanm --notest \
            Cairo \
            DBI \
            Gtk2 \
            Tk \
            Sort::Naturally

    sudo apt-get update \
        && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
        && apt-get install -y nodejs

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

    wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O cpanm \
        && chmod +x ./cpanm \
        && ./cpanm --notest \
            Cairo \
            DBI \
            Gtk2 \
            Tk \
            Sort::Naturally

    sudo apt-get update \
        && curl -sL https://deb.nodesource.com/setup_8.x | bash - \
        && apt-get install -y \
            nodejs

else
    echo "Unexpected operating system: $PLATFORM"
    exit 1
fi;


mkdir seqr_settings
cp ${SEQR_DIR}/deploy/docker/seqr/config/*.py seqr_settings/

# install venv
curl -Lo virtualenv-16.0.0.tar.gz https://pypi.python.org/packages/source/v/virtualenv/virtualenv-16.0.0.tar.gz
tar xzf virtualenv-16.0.0.tar.gz
python virtualenv-16.0.0/virtualenv.py --python=python2.7 venv
rm -rf virtualenv-16.0.0*

# activate venv
echo "source venv/bin/activate" > activate_virtualenv.sh
chmod 666 activate_virtualenv.sh  # this script must be sourced rather than executed
source activate_virtualenv.sh

# install python dependencies
pip install --upgrade -r requirements.txt

# init django
python -u manage.py makemigrations
python -u manage.py migrate
python -u manage.py check
python -u manage.py collectstatic --no-input

GUNICORN_WORKER_THREADS=4

echo 'cd '${SEQR_DIR}'/seqr_settings
LOG_FILE=gunicorn.log
nohup gunicorn -w '${GUNICORN_WORKER_THREADS}' -c gunicorn_config.py wsgi:application >& ${LOG_FILE} &
echo "gunicorn started in background. See ${LOG_FILE}"
' > start_server.sh

./start_server.sh

