source ./environment

export MY_PATH=$(dirname $(readlink -f "$0"))

cd $INSTALL_DIR

echo '===================='
echo '    INIT'
echo '===================='


${MY_PATH}/scripts/init/install_cli_tools.CentOS.sh
${MY_PATH}/scripts/init/create_unix_users.sh

sudo su seqr -c bash <<EOF

source ${MY_PATH}/environment

pkill mongo
pkill gunicorn
pkill xwiki

# pkill supervisord


${MY_PATH}/scripts/init/create_directories.sh
${MY_PATH}/scripts/init/add_paths_to_bashrc.sh

source ~/.bashrc

echo '===================='
echo '    POSTGRES'
echo '===================='

${MY_PATH}/scripts/postgres/install_postgres.CentOS.sh
${MY_PATH}/scripts/postgres/init_databases.sh
${MY_PATH}/scripts/postgres/start_postgres.sh

sleep 5;   # wait for postgres to start up 

if [ -n "$SEQR_DB_BACKUP" ]; then 
    ${MY_PATH}/scripts/postgres/restore_db_from_backup.sh $SEQR_DB_BACKUP
fi

if [ -n "$PHENOTIPS_DB_BACKUP" ]; then 
    ${MY_PATH}/scripts/postgres/restore_db_from_backup.sh $PHENOTIPS_DB_BACKUP
fi

echo '===================='
echo '    MONGO'
echo '===================='

cd $INSTALL_DIR
${MY_PATH}/scripts/mongo/install_mongo.sh
${MY_PATH}/scripts/mongo/start_mongod.sh

echo '===================='
echo '    PHENOTIPS'
echo '===================='

${MY_PATH}/scripts/phenotips/install_phenotips.sh
${MY_PATH}/scripts/phenotips/start_phenotips.sh

echo '===================='
echo '    SEQR'
echo '===================='

${MY_PATH}/scripts/seqr/clone_seqr_repo.sh
${MY_PATH}/scripts/seqr/download_reference_data.sh
${MY_PATH}/scripts/seqr/install_python_deps.sh
${MY_PATH}/scripts/seqr/init_seqr.sh


echo '===================='
echo '    WEBSERVER'
echo '===================='

${MY_PATH}/scripts/gunicorn/install_gunicorn.sh
${MY_PATH}/scripts/gunicorn/start_gunicorn.sh


#echo '===================='
#echo '    SUPERVISORD'
#echo '===================='
#
#${MY_PATH}/scripts/supervisord/install_supervisord.sh
#${MY_PATH}/scripts/supervisord/stop_supervisord.sh
#${MY_PATH}/scripts/supervisord/start_supervisord.sh

#${MY_PATH}/seqr/migrate_database.sh
#${MY_PATH}/seqr/transfer_to_new_schema.sh

EOF



echo '===================='
echo '    NGINX'
echo '===================='


${MY_PATH}/scripts/nginx/install_nginx.CentOS.sh

