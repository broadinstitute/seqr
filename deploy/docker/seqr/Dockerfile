############################
# UI build (Node.js 14 only)
############################
FROM node:14-bullseye AS ui-build

WORKDIR /build/ui

# Copy package metadata first for better caching
COPY ./ui/package.json .
COPY ./ui/package-lock.json .

# npm v7 for lockfile v2 compatibility
RUN npm install -g npm@7.24.2 \
    && npm ci

# Copy the rest of the UI source and build
COPY ./ui/ .
RUN npm run build


############################
# Python build stage
############################
FROM python:3.11-slim-bullseye AS build

LABEL maintainer="Broad TGG"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    bzip2 \
    curl \
    gcc \
    libc6-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /opt
COPY ./requirements.txt .

# Install seqr Python dependencies
RUN pip install --no-cache-dir wheel \
    && pip install --no-cache-dir -U setuptools \
    && pip install --no-cache-dir -r requirements.txt


############################
# Runtime stage
############################
FROM python:3.11-slim-bullseye AS runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    curl \
    emacs \
    gnupg \
    htop \
    less \
    libpq-dev \
    nano \
    postgresql-client \
    procps \
    redis-tools \
    xterm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install gcloud tools
RUN echo "deb http://packages.cloud.google.com/apt cloud-sdk-bullseye main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python virtualenv from build stage
COPY --from=build /opt/venv /opt/venv

WORKDIR /seqr

# Copy application code
COPY admin/ ./admin
COPY clickhouse_search/ ./clickhouse_search
COPY matchmaker/ ./matchmaker
COPY panelapp/ ./panelapp
COPY reference_data/ ./reference_data
COPY seqr/ ./seqr
COPY manage.py settings.py wsgi.py ./

# Copy built UI assets
COPY --from=ui-build /build/ui/dist /seqr/ui/dist

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN ./manage.py collectstatic --no-input

EXPOSE 8000
ENV TERM=xterm

COPY deploy/docker/seqr/readiness_probe /
COPY deploy/docker/seqr/wait_for_routes /
COPY deploy/docker/seqr/clickhouse_backup.py /
COPY deploy/docker/seqr/bin/*.sh /usr/local/bin/
COPY deploy/docker/seqr/config/*.py ./
COPY deploy/docker/seqr/bashrc /root/.bashrc
COPY deploy/docker/seqr/entrypoint.sh /

CMD ["/entrypoint.sh"]
