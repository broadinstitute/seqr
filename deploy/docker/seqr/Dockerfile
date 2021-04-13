FROM google/cloud-sdk:335.0.0

WORKDIR /opt/seqr

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT
ENV PATH $PATH:/root/google-cloud-sdk/bin
EXPOSE $SEQR_SERVICE_PORT

ADD requirements.txt /opt/

# install commmon utilities
RUN apt update && apt install -y --no-install-recommends \
    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    libgtk2-perl libdbi-perl libtk-perl libsort-naturally-perl && \
    apt clean && rm -rf /var/lib/apt/lists/*

# install seqr dependencies
RUN pip install -r /opt/requirements.txt

ADD matchmaker /opt/seqr/matchmaker
ADD reference_data /top/seqr/reference_data
ADD seqr /top/seqr/seqr
ADD static /top/seqr/actstatic
ADD deploy/docker/seqr/entrypoint.sh deploy/docker/seqr/init_db.sh deploy/docker/seqr/config/ /opt/

# Berglass: Store and retrieve secrets on Google Cloud
COPY --from=us-docker.pkg.dev/berglas/berglas/berglas:latest /bin/berglas /bin/berglas

ENTRYPOINT exec /bin/berglas exec -- /opt/entrypoint.sh
