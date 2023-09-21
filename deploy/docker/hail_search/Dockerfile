FROM hailgenetics/hail:0.2.115

LABEL maintainer="Broad TGG"

WORKDIR /hail_search

# Install dependencies.
# (Explicitly not using a build image w/ venev here because our additional requirements are minimal... for now)
COPY hail_search/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Deployment utilities
COPY deploy/docker/hail_search/gunicorn_config.py /
COPY deploy/docker/hail_search/readiness_probe /
COPY deploy/docker/hail_search/start_server.sh /

# Application Code
COPY hail_search/ .

WORKDIR /
EXPOSE 8000
CMD ["/start_server.sh"]