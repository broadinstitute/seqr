#!/usr/bin/env bash

export PLATFORM=$(python -c "import sys; print(sys.platform)")


if [ $PLATFORM = "darwin" ]; then

    echo "==== Installing postgres using brew ===="

    brew install postgres


elif [ $PLATFORM = "centos" ]; then

    echo "==== Installing postgres using yum ===="

    sudo yum install -y postgresql postgresql-server postgresql-contrib

    sudo postgresql-setup initdb
    sudo sed -i s/peer/trust/  /var/lib/pgsql/data/pg_hba.conf
    sudo sed -i s/ident/trust/  /var/lib/pgsql/data/pg_hba.conf
    sudo service postgresql start


elif [ $PLATFORM = "ubuntu" ]; then

    echo "==== Installing postgres using apt-get ===="

    sudo apt-get install -y postgresql postgresql-contrib postgresql-client

    sudo sed -i s/peer/trust/ $(find /etc/postgresql -name "pg_hba.conf")
    sudo systemctl enable postgresql.service
    sudo systemctl start postgresql.service


else
    echo "Unexpected operating system: $PLATFORM"
    exit 1;
fi;