set -x

export MY_PATH=$(dirname $(readlink -f "$0"))

mkdir -p gunicorn # && sudo chown gunicorn:gunicorn gunicorn

cd seqr

# install the supervisord.conf
cat ${MY_PATH}/conf/gunicorn_config.py | \
    python -c "import sys; print sys.stdin.read().replace('\${INSTALL_DIR}', '${INSTALL_DIR}')"  | \
    tee gunicorn_config.py
