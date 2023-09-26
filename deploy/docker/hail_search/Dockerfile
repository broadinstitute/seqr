FROM hailgenetics/hail:0.2.115

LABEL maintainer="Broad TGG"

WORKDIR /hail_search

# Infrastucture Code
COPY deploy/docker/hail_search/sync_datasets /

# Application Code
COPY hail_search/ .

WORKDIR /
EXPOSE 8000
CMD ["python3", "-m", "hail_search"]
