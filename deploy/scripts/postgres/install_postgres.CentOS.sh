set -x

export MY_PATH=$(dirname $(readlink -f "$0"))


mkdir -p postgres/datadir; chmod 700 postgres/datadir
cd postgres

POSTGRES_TAR_FILE=postgresql-9.6.1-1-linux-x64-binaries.tar.gz
wget -N -c -O $POSTGRES_TAR_FILE 'https://www.enterprisedb.com/postgresql-948-binaries-linux64?ls=Crossover&type=Crossover'
tar xzf $POSTGRES_TAR_FILE

cp ${MY_PATH}/conf/*.conf .

cat ${MY_PATH}/conf/postgresql.conf | python -c 'import sys; print sys.stdin.read().replace('\''${INSTALL_DIR}'\'', '\''/local/software'\'')' | tee ${INSTALL_DIR}/postgres/postgresql.conf

for f in ${MY_PATH}/*.sh; do
    cat $f | python -c 'import sys; print sys.stdin.read().replace('\''${INSTALL_DIR}'\'', '\''/local/software'\'')' | tee ${INSTALL_DIR}/postgres/`basename $f`
    chmod 777 ${INSTALL_DIR}/postgres/`basename $f`
done
