#!/usr/bin/env bash

echo "==== Installing seqr ===="
set -x

if [ -z "$PLATFORM" ]; then

    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1;

elif [ $PLATFORM = "macos" ]; then

    :

elif [ $PLATFORM = "centos" ]; then

    echo "==== Installing seqr dependencies using yum ===="

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

    echo "==== Installing seqr dependencies using apt-get ===="

    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    sudo apt-get install -y \
        build-essential \
        libcairo2-dev \
        libglib2.0-bin \
        libglib2.0-0 \
        libgtk2.0-dev \
        libpango1.0-dev

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

else
    echo "Unexpected operating system: $PLATFORM"
    exit 1;
fi;


pip install -r requirements.txt

mkdir seqr_settings

cp -r ${SEQR_DIR}/deploy/docker/seqr/config

set +x