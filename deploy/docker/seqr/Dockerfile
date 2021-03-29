FROM python:3.7-buster

LABEL maintainer="Broad TGG"

# install commmon utilities
RUN apt update && apt install -y --no-install-recommends \
    bzip2 \
    curl \
    git \
    # install dependencies of the HaploPainter.pl script used to generate static pedigree images
    perl \
    build-essential \
    libcairo2-dev \
    libglib2.0-bin \
    libglib2.0-0 \
    libgtk2.0-dev \
    libpango1.0-dev \
    # install database clients for debugging (https://www.postgresql.org/download/linux/debian/)
    postgresql-11 \
    postgresql-client-11 \
    libpq-dev \
    redis-tools \
    # install dev dependencies for react, javascript development. These are not needed at runtime.
    nodejs && \
    apt clean && rm -rf /var/lib/apt/lists/* && \
    curl -L0 https://raw.github.com/miyagawa/cpanminus/master/cpanm -o /usr/bin/cpanm && \
    chmod +x /usr/bin/cpanm && \
    cpanm --notest \
    Cairo \
    DBI \
    Gtk2 \
    Tk \
    Sort::Naturally && \
    # install gcloud tools
    curl https://sdk.cloud.google.com | bash

ARG SEQR_REPO=https://github.com/populationgenomics/seqr
ARG SEQR_GIT_SHA

# update seqr repo
RUN git clone -q $SEQR_REPO seqr && \
    cd seqr && \
    git checkout $SEQR_GIT_SHA && \
    # install seqr dependencies
    pip install -r requirements.txt && \
    cd deploy/docker/seqr && \
    cp readiness_probe entrypoint.sh / && \
    cp bin/*.sh /usr/local/bin/ && \
    cp gitconfig /root/.gitconfig && \
    cp config/*.py ./ && \
    cp bashrc /root/.bashrc

ARG SEQR_SERVICE_PORT
ENV SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT

EXPOSE $SEQR_SERVICE_PORT

COPY --from=us-docker.pkg.dev/berglas/berglas/berglas:latest /bin/berglas /bin/berglas

ENTRYPOINT exec /bin/berglas exec -- /entrypoint.sh
