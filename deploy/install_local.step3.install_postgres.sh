#!/usr/bin/env bash

echo "==== Installing postgres ===="
set -x

if [ -z "$PLATFORM" ]; then

    echo "PLATFORM environment variable not set. Please run previous install step(s)."
    exit 1;

elif [ $PLATFORM = "macos" ]; then

    brew install postgres

elif [ $PLATFORM = "centos" ]; then

    sudo yum install -y postgresql postgresql-server postgresql-contrib

    sudo postgresql-setup initdb
    sudo sed -i s/peer/trust/  /var/lib/pgsql/data/pg_hba.conf
    sudo sed -i s/ident/trust/  /var/lib/pgsql/data/pg_hba.conf
    sudo service postgresql start

elif [ $PLATFORM = "ubuntu" ]; then

    sudo apt-get install -y postgresql postgresql-contrib postgresql-client

    sudo sed -i s/peer/trust/ $(find /etc/postgresql -name "pg_hba.conf")
    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service

else

    echo "Unexpected operating system: $PLATFORM"
    exit 1;
fi;

set +x