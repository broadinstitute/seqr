set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

mkdir -p phenotips && cd phenotips

# download from https://phenotips.org/Download
wget -c -N https://nexus.phenotips.org/nexus/content/repositories/releases/org/phenotips/phenotips-standalone/1.3-milestone-5/phenotips-standalone-1.3-milestone-5.zip && unzip -n phenotips-standalone-1.3-milestone-5.zip
wget -c -N https://jdbc.postgresql.org/download/postgresql-9.4.1212.jre6.jar -O ./phenotips-standalone-1.3-milestone-5/webapps/phenotips/WEB-INF/lib/postgresql-9.4-1206-jdbc4.jar

cp ${MY_PATH}/conf/hibernate.cfg.xml phenotips-standalone-1.3-milestone-5/webapps/phenotips/WEB-INF/
