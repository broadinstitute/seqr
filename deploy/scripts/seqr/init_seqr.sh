cd ${INSTALL_DIR}/seqr

python manage.py makemigrations
python manage.py migrate

python manage.py collectstatic --noinput
