FROM python:3.13@sha256:f878b01bbb7c91935220077a3b43f9846b466b14ddc916ce83f30913d077bb36 AS barkoder

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

FROM python:3.13-slim@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669

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
# COPY .git_hash /app/git_hash

ENV DJANGO_SETTINGS_MODULE=vdv_pkpass.settings_dev \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY entrypoint.sh /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000
