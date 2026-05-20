FROM python:3.11-slim-bullseye

LABEL maintainer="Broad TGG"

RUN pip install --no-cache-dir -r vlm/requirements.txt

WORKDIR /vlm

# Application Code
COPY vlm/ .

WORKDIR /
EXPOSE 7000
CMD ["python3", "-m", "vlm"]
