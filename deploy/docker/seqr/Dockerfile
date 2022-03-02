FROM python:3.7-slim-bullseye as build

LABEL maintainer="Broad TGG"

# install commmon utilities, database clients for debugging
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    bzip2 \
    curl \
    gcc \
    libc6-dev \
    libpq-dev \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /opt

COPY ./requirements.txt .

# install seqr dependencies
RUN pip install --no-cache-dir wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    ln -s python3 /opt/venv/bin/python3.7

WORKDIR /build

COPY ./ui ./ui

WORKDIR /build/ui
RUN npm ci && \
    npm run build

FROM python:3.7-slim-bullseye as runtime

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

# install gcloud tools
RUN echo "deb http://packages.cloud.google.com/apt cloud-sdk-bullseye main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update && apt-get install -y --no-install-recommends \
        google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/venv /opt/venv

WORKDIR /seqr
COPY . .
COPY --from=build /build/ui/dist /seqr/ui/dist

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN ./manage.py collectstatic --no-input

EXPOSE 8000

ENV TERM=xterm

COPY deploy/docker/seqr/readiness_probe /
COPY deploy/docker/seqr/bin/*.sh /usr/local/bin/
COPY deploy/docker/seqr/config/*.py ./
COPY deploy/docker/seqr/bashrc /root/.bashrc

COPY deploy/docker/seqr/entrypoint.sh /

CMD [ "/entrypoint.sh" ]
