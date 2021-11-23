FROM python:3.7-slim-buster

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT
EXPOSE $SEQR_SERVICE_PORT

WORKDIR /app/seqr
COPY requirements.txt /app/seqr/

RUN apt update && apt install -y --no-install-recommends \
    apt-transport-https ca-certificates curl gnupg \
    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    libgtk2-perl libdbi-perl libtk-perl libsort-naturally-perl && \
    # Google Cloud SDK
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
    apt update && apt install -y google-cloud-sdk && \
    apt clean && rm -rf /var/lib/apt/lists/* && \
    pip install -r /app/seqr/requirements.txt

COPY matchmaker /app/seqr/matchmaker
COPY reference_data /app/seqr/reference_data
COPY seqr /app/seqr/seqr
COPY static ui/dist /app/seqr/static
COPY ui/dist /app/seqr/ui/dist
COPY panelapp /app/seqr/panelapp
COPY wsgi.py settings.py servctl manage.py deploy/docker/seqr/entrypoint.sh deploy/docker/seqr/init_db.sh deploy/docker/seqr/config/ deploy/docker/seqr/update_reference_server.py /app/seqr

# Berglass: Store and retrieve secrets on Google Cloud
COPY --from=us-docker.pkg.dev/berglas/berglas/berglas:latest /bin/berglas /bin/berglas

ENTRYPOINT exec /bin/berglas exec -- /app/seqr/entrypoint.sh
