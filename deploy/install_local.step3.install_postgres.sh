#!/usr/bin/env bash

echo "==== Installing postgres ===="
set -x

if [ -z "$PLATFORM" ]; then
    set +x
    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    brew install postgres

elif [ $PLATFORM = "centos" ]; then
    wget https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-7-x86_64/pgdg-centos96-9.6-3.noarch.rpm
    sudo yum install -y pgdg-centos96-9.6-3.noarch.rpm epel-release

    sudo yum update
    sudo yum install -y postgresql96 postgresql96-server postgresql96-contrib


    PG_HBA_PATH=/var/lib/pgsql/data/pg_hba.conf
    sudo sed -i s/peer/trust/  $PG_HBA_PATH
    sudo sed -i s/ident/trust/  $PG_HBA_PATH

    sudo /usr/pgsql-9.6/bin/postgresql96-setup initdb
    sudo systemctl enable postgresql-9.6
    sudo systemctl start postgresql-9.6

elif [ $PLATFORM = "ubuntu" ]; then

    sudo apt-get install -y postgresql postgresql-contrib postgresql-client

    PG_HBA_PATH=$(find /etc/postgresql -name "pg_hba.conf")
    sudo sed -i s/peer/trust/ $PG_HBA_PATH
    sudo sed -i s/md5/trust/ $PG_HBA_PATH

    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service

else
    set +x
    echo "Unexpected operating system: $PLATFORM"
    exit 1

fi;

set +x