#!/usr/bin/env bash

set +x
set +x

if [ -z "$SEQR_DIR"  ]; then
    echo "SEQR_DIR environment variable not set. Please run install_general_dependencies.sh as described in step 1 of https://github.com/macarthur-lab/seqr/blob/master/deploy/LOCAL_INSTALL.md"
    exit 1
fi

echo
echo "==== Installing Phenotips ===="
echo
set -x

export PT_VERSION="1.2.6"
wget -nv https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/${PT_VERSION}/phenotips-standalone-${PT_VERSION}.zip \
    && unzip -o phenotips-standalone-${PT_VERSION}.zip \
    && rm phenotips-standalone-${PT_VERSION}.zip

cd phenotips-standalone-${PT_VERSION}
wget -nv https://jdbc.postgresql.org/download/postgresql-42.1.4.jar -O ./webapps/phenotips/WEB-INF/lib/postgresql-42.1.4.jar

cp ${SEQR_DIR}/deploy/docker/phenotips/config/${PT_VERSION}/xwiki.cfg ./webapps/phenotips/WEB-INF/xwiki.cfg
cp ${SEQR_DIR}/deploy/docker/phenotips/config/${PT_VERSION}/hibernate.cfg.xml ./webapps/phenotips/WEB-INF/hibernate.cfg.xml
sed -i.bak 's/<property.name="connection.url">.*<\/property>/<property name="connection.url">jdbc:postgresql:\/\/localhost:5432\/xwiki<\/property>/' ./webapps/phenotips/WEB-INF/hibernate.cfg.xml

rm -rf data/extension data/jobs
cp -r ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/extension ./data/extension
cp -r ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/jobs ./data/jobs

# init PhenoTips db
psql -U postgres postgres -c "create role xwiki with CREATEDB LOGIN PASSWORD 'xwiki'"
psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'
psql -U xwiki postgres -c 'create database xwiki'
psql -U xwiki xwiki -f ${SEQR_DIR}/deploy/docker/phenotips/init/${PT_VERSION}/init_phenotips_db.sql

echo 'cd '$(pwd)'
LOG_FILE=$(pwd)/phenotips.log
(nohup ./start.sh >& ${LOG_FILE}) &
echo "PhenoTips started in background on port 8080. See ${LOG_FILE}"
' | tee start_phenotips.sh
chmod 777 ./start_phenotips.sh

set +x

./start_phenotips.sh

cd ..
