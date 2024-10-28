# vdv-pkpass

## How to run it locally

Don't. Q didn't intend it that way.

Maya disagreed.

## Getting ready to run it locally

### System dependencies

```shell
apt install libldap2-dev libsasl2-dev slapd ldap-utils
```

### Python

Using `python3.13`:

```shell
apt install software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install python3.13 python3.13-pip python3.13-dev
```

#### Using venv

```shell
python3.13 -m venv venv
source venv/bin/activate
```

#### Python dependencies

```shell
pip install -r requirements.txt
```

### Compiling Barkoder

```shell
# Dependencies
apt install -y build-essential gcc cmake libgl1 libcurl4-openssl-dev pkg-config
pip install pybind11[global]

# Build folder
mkdir -p barkoder/build
cd barkoder/build

# Build
cmake .. && make

# Copy to site-packages
cd ../..
cp ./barkoder/build/Barkoder.cpython-313-x86_64-linux-gnu.so ./env_vdv_pkpass/lib/python3.13/site-packages/
```

### Other changes

In `./manage.py:9` set to:

```py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vdv_pkpass.settings_dev")
```

### Django

```shell
mkdir -p ./uid-data
mkdir -p ./vdv-certs
python manage.py migrate
python manage.py download-uic-data
python manage.py download-vdv-certs
python manage.py download-vdv-orgs
```

## Running it locally

```shell
python manage.py runserver
```

## Conclusion

With all this... it *should* work (*should* as defined in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119))
