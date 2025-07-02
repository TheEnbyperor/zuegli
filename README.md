# Zügli

Convert your barcoded train tickets into Apple/Google Wallet passes - or just look at what's encoded inside them.

Available online at [zügli.app](https://xn--zgli-0ra.app).

## How to run it locally

Don't. Q didn't intend it that way.

## So you've insisted on running it locally anyway
### The nix/"easy" way

. Have [nix package manager](https://nixos.org/download/) installed, and [direnv](https://direnv.net/) integrated into your shell.
. From this directory, run `direnv allow` to automatically configure and load all software dependencies
. Run the `initialise` script to run migrations and download supplemental data
. Run `python manage.py runserver` to run the server

### The Debian way

#### System dependencies

```shell
apt install libldap2-dev libsasl2-dev slapd ldap-utils
```

#### Python

Using `python3.13`:

```shell
# Fedora
sudo yum install python3-pip python3

# Debian/Ubuntu/etc
apt install software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install python3.13 python3.13-pip python3.13-dev
```

##### Using venv

```shell
python3.13 -m venv venv
source venv/bin/activate
```

##### Python dependencies

```shell
pip install -r requirements.txt
```

#### Compiling Barkoder

```shell
# Dependencies for Debian/Ubuntu/etc
apt install -y build-essential gcc cmake libgl1 libcurl4-openssl-dev pkg-config

# Dependencies for Fedora
yum install -y g++ gcc cmake openssl-devel libcurl-devel pkg-config

pip install pybind11[global]

# Build folder
mkdir -p barkoder/build
cd barkoder/build

# Build
cmake .. && make

# Copy to site-packages (run in activated virtualenv)
cd ../..
cp ./barkoder/build/Barkoder.cpython-313-x86_64-linux-gnu.so "$(python -c 'import site; print(site.getsitepackages()[0])')"
```

#### Install RabbitMQ

RabbitMQ is required for celery to work. The default configuration is often enough for a development environment.

```shell

# Debian etc.
apt install -y rabbitmq-server

# Fedora/RHEL etc.
yum install -y rabbitmq-server

systemctl start rabbitmq-server # or 'enable --now rabbitmq-server' if you want it to start by default on boot
```

#### Other changes

Set an environment environment variable to use development settings:

```sh
export DJANGO_SETTINGS_MODULE="vdv_pkpass.settings_dev"
```

or change `./manage.py:9` to:

```py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vdv_pkpass.settings_dev")
```

#### Django

```shell
mkdir -p ./uic-data
mkdir -p ./vdv-certs
python manage.py migrate
```

#### Run webserver and celery

In two separate windows, start the webserver and celery:

```shell
python manage.py runserver
```

```shell
celery -A vdv_pkpass worker
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
