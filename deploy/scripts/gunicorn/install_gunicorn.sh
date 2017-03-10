set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

mkdir -p gunicorn # && sudo chown gunicorn:gunicorn gunicorn

cd seqr

# install the supervisord.conf

cat ${MY_PATH}/conf/gunicorn_config.py | python -c "import sys; print sys.stdin.read().replace('\${INSTALL_DIR}', '${INSTALL_DIR}')"  | tee gunicorn_config.py


for f in ${MY_PATH}/s*.sh; do
    cat $f | python -c 'import sys; print sys.stdin.read().replace('\''${INSTALL_DIR}'\'', '\''/local/software'\'')' | tee ${INSTALL_DIR}/gunicorn/`basename $f`
    chmod 777 ${INSTALL_DIR}/gunicorn/`basename $f`
done
