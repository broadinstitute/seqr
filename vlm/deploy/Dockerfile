FROM hailgenetics/hail:0.2.128

LABEL maintainer="Broad TGG"

WORKDIR /vlm

# Application Code
COPY vlm/ .

WORKDIR /
EXPOSE 6000
CMD ["python3", "-m", "vlm"]
