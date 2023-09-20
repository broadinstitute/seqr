FROM hailgenetics/hail:0.2.115

LABEL maintainer="Broad TGG"

WORKDIR /hail_search

# Deployment utilities
COPY deploy/docker/seqr/config/*.py ./
COPY deploy/docker/hail_search/readiness_probe /

# Application Code
COPY ./hail_search/ .

EXPOSE 8000
CMD [ "python3", "-m", "hail_search" ]