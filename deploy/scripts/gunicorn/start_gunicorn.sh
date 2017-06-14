cd ${INSTALL_DIR}/seqr
nohup gunicorn -w 4 -c gunicorn_config.py wsgi:application --timeout 3600 >& ${INSTALL_DIR}/logs/gunicorn.log &
# less +F ${INSTALL_DIR}/logs/gunicorn.log
