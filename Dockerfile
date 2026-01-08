FROM python:3.13 AS barkoder

RUN set -eux ; \
    apt-get update -qq ; \
    apt-get install -qqy --no-install-recommends \
    cmake \
    libcurl4-openssl-dev \
    libgl1 \
    pkg-config \
    ; \
    rm -rf /var/lib/apt/lists/* ; \
    pip install -q --no-cache-dir -U pip pybind11[global] ;

COPY barkoder /barkoder

WORKDIR /barkoder/build

RUN cmake .. && make

FROM python:3.13-slim

WORKDIR /app/

RUN set -eux ; \
    useradd app ; \
    apt-get update -qq ; \
    apt-get install -qqy --no-install-recommends \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libldap2-dev \
    libsasl2-dev \
    libsasl2-modules \
    libssl-dev \
    pkg-config \
    ; \
    rm -rf /var/lib/apt/lists/* ; \
    pip install -q --no-cache-dir -U pip ;

COPY requirements.txt /app/

RUN set -eux ; \
    pip install -q --no-cache-dir -r requirements.txt ; \
    rm requirements.txt ;

RUN set -eux ; \
    apt-get remove -y \
    gcc \
    ; \
    apt-get autoremove -y ; \
    apt-get clean ;

USER app:app

COPY --from=barkoder /barkoder/build/Barkoder.cpython-313-x86_64-linux-gnu.so /usr/local/lib/python3.13/site-packages/Barkoder.cpython-313-x86_64-linux-gnu.so
COPY gtfs /app/gtfs
COPY main /app/main
COPY manage.py /app/manage.py
COPY vdv_pkpass /app/vdv_pkpass
COPY .git_hash /app/git_hash
COPY entrypoint.sh /app/entrypoint.sh

RUN set -eux ; \
    chown -R app:app /app/ ; \
    chmod +x /app/entrypoint.sh ;

ENV DJANGO_SETTINGS_MODULE=vdv_pkpass.settings_dev \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000
