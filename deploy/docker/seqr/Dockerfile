FROM google/cloud-sdk:335.0.0

ARG SEQR_REPO=https://github.com/populationgenomics/seqr
ARG SEQR_GIT_SHA
ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT
ENV PATH $PATH:/root/google-cloud-sdk/bin
EXPOSE $SEQR_SERVICE_PORT

# install commmon utilities
RUN apt update && apt install -y --no-install-recommends \
    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    libgtk2-perl libdbi-perl libtk-perl libsort-naturally-perl && \
    apt clean && rm -rf /var/lib/apt/lists/* && \
    # update seqr repo
    git clone -q $SEQR_REPO seqr && \
    cd seqr && \
    git checkout $SEQR_GIT_SHA && \
    rm -r .git && \
    # install seqr dependencies
    pip install -r requirements.txt

COPY --from=us-docker.pkg.dev/berglas/berglas/berglas:latest /bin/berglas /bin/berglas

ENTRYPOINT exec /bin/berglas exec -- /seqr/deploy/docker/seqr/entrypoint.sh
