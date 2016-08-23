FROM python:2.7-alpine
MAINTAINER Kennedy Brown | thoughtarray

# Overlay S6
ADD https://github.com/just-containers/s6-overlay/releases/download/v1.18.1.3/s6-overlay-amd64.tar.gz /tmp/
RUN tar xzf /tmp/s6-overlay-amd64.tar.gz -C / && rm /tmp/s6-overlay-amd64.tar.gz

# Install testapp
COPY . /tmp/testapp
WORKDIR /tmp/testapp

RUN pip install -r /tmp/testapp/requirements.txt \
  && python /tmp/testapp/setup.py install \
  && rm -r /tmp/testapp

WORKDIR /

EXPOSE 80
ENTRYPOINT ["/init", "testapp"]
