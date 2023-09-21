FROM hailgenetics/hail:0.2.115

LABEL maintainer="Broad TGG"

WORKDIR /hail_search

# Application Code
COPY hail_search/ .

WORKDIR /
EXPOSE 8000
CMD ["python", "-m", "hail_search"]
