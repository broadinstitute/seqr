FROM python:2.7.11

MAINTAINER MacArthur Lab

RUN git clone -q https://github.com/macarthur-lab/seqr

WORKDIR seqr

# install seqr dependencies
RUN pip install --upgrade pip gunicorn \
    && pip install --upgrade -r requirements.txt

# install dependencies of generate_pedigree_images command which generates static images using HaploPainter.pl
RUN apt-get update \
    && apt-get install -y perl build-essential libcairo2-dev libgtk2.0-dev libglib2.0-bin libglib2.0-0 libpango1.0-dev \
    && wget https://raw.github.com/miyagawa/cpanminus/master/cpanm -O /usr/bin/cpanm \
    && chmod +x /usr/bin/cpanm \
    && cpanm --notest Cairo DBI Gtk2 Tk Sort::Naturally

ENV PYTHONPATH=/seqr:/seqr_settings

COPY config/*.py  /seqr_settings/

EXPOSE 8000

COPY entrypoint.sh .

CMD ["./entrypoint.sh"]
