FROM python:3.12-slim

ARG ZONT_API_VERSION

WORKDIR /app

COPY examples/zont_prom_exporter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dist/zont_api-${ZONT_API_VERSION}-py3-none-any.whl /tmp
RUN pip install /tmp/zont_api-${ZONT_API_VERSION}-py3-none-any.whl

COPY examples/zont_prom_exporter/zont_prom_exporter.py .

CMD [ "python", "./zont_prom_exporter.py" ]
