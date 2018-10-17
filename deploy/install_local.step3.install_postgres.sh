#!/usr/bin/env bash

echo "==== Installing postgres ===="
set -x

if [ -z "$PLATFORM" ]; then

    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1

elif [ $PLATFORM = "macos" ]; then

    brew install postgres

elif [ $PLATFORM = "centos" ]; then

    sudo yum install -y postgresql postgresql-server postgresql-contrib

    PG_HBA_PATH=/var/lib/pgsql/data/pg_hba.conf
    sudo sed -i s/peer/trust/  $PG_HBA_PATH
    sudo sed -i s/ident/trust/  $PG_HBA_PATH

    sudo postgresql-setup initdb
    sudo service postgresql start

elif [ $PLATFORM = "ubuntu" ]; then

    sudo apt-get install -y postgresql postgresql-contrib postgresql-client

    PG_HBA_PATH=$(find /etc/postgresql -name "pg_hba.conf")
    sudo sed -i s/peer/trust/ $PG_HBA_PATH
    sudo sed -i s/md5/trust/ $PG_HBA_PATH

    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service

else

    echo "Unexpected operating system: $PLATFORM"
    exit 1

fi;

set +x