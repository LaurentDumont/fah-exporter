FROM python:3.8.2-alpine3.11
LABEL description="Folding@Home client exporter" \
  version="1.0" \
  maintainer="Laurent Dumont - ldumont@northernsysadmin.com"

COPY requirements.txt requirements.txt

RUN \
  pip3 install -r requirements.txt;

COPY fah-exporter.py fah-exporter.py

ENTRYPOINT ["python3", "fah-exporter.py"]
