FROM hailgenetics/hail:0.2.128

LABEL maintainer="Broad TGG"

WORKDIR /hail_search

# Application Code
COPY hail_search/ .

WORKDIR /
EXPOSE 5000
CMD ["python3", "-m", "hail_search"]
