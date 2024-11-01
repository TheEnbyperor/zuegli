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

## Tests

Using [Muster-Tickets nach UIC 918.9](https://assets.static-bahn.de/dam/jcr:95540b93-5c38-4554-8f00-676214f4ba76/Muster%20918-9.zip) as provided by Deutsche Bahn:

- [x] `Muster 918-9 FV_SuperSparpreis.pdf`
- [x] `Muster 918-9 FV_SuperSparpreis_2Erw.pdf`
- [x] `Muster 918-9 FV_SuperSparpreis_3Erw_InklRückfahrt.pdf`
- [x] `Muster 918-9 FV_SuperSparpreisSenior_InklRückfahrt.pdf`
- [x] `Muster 918-9 FV_SuperSparpreisYoung.pdf`
- [x] `Muster 918-9 Länderticket Bayern Nacht.pdf`
- [x] `Muster 918-9 Länderticket Rheinland-Pfalz.pdf`
- [x] `Muster 918-9 Länderticket Saarland.pdf`
- [x] `Muster 918-9 Länderticket Sachsen-Anhalt.pdf`
- [x] `Muster 918-9 Länderticket Thüringen.pdf`
- [x] `Muster 918-9 Normalpreis.pdf`
- [x] `Muster 918-9 Quer-durchs-Land Ticket.pdf`
- [x] `Muster 918-9 Schleswig-Holstein Ticket.pdf`
- [x] `Muster 918-9 BahnCard 25.png`
- [x] `Muster 918-9 CityTicket.pdf`
- [x] `Muster 918-9 CityTicket_International.pdf`
- [x] `Muster 918-9 Deutschland-Jobticket.png`
- [x] `Muster 918-9 Deutschland-Ticket.png`
