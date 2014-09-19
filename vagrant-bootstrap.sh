#!/usr/bin/env bash
set -xe

# switch to NZ Ubuntu mirrors
sed -i 's/us\.archive/nz.archive/' /etc/apt/sources.list

# Add ubuntugis ppa
sudo add-apt-repository ppa:ubuntugis/ppa

# upgrade some packages
apt-get update
apt-get remove -y redis-server mongodb-org-server
apt-get upgrade -y

# install other dependencies
apt-get install -y libgeos-c1 libgeos-dev

# Build PostGIS
apt-get install -y postgresql-server-dev-9.3 libxml2-dev libproj-dev libjson0-dev xsltproc docbook-xsl docbook-mathml
su vagrant <<EOSU
wget --no-verbose http://download.osgeo.org/postgis/source/postgis-2.1.3.tar.gz
tar xfz postgis-2.1.3.tar.gz
cd postgis-2.1.3
./configure --without-raster --without-topology
make
sudo make install 
sudo ldconfig
EOSU

# Create the database
su postgres <<EOSU
psql postgres -c "CREATE ROLE vagrant LOGIN SUPERUSER PASSWORD 'vagrant';"
createdb prop_xfer -O vagrant -E utf8
psql prop_xfer -f /usr/share/postgresql/9.3/contrib/postgis-2.1/postgis.sql
psql prop_xfer -f /usr/share/postgresql/9.3/contrib/postgis-2.1/spatial_ref_sys.sql
EOSU
echo "export DATABASE_URL=postgresql:///prop_xfer" >> /home/vagrant/.profile

# Setup our python app
su - vagrant <<EOSU
#set -xe
export WORKON_HOME=/home/vagrant/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv venv
workon venv
pip install -r /vagrant/requirements.txt
add2virtualenv /vagrant

# helpful stuff
pip install ipython==1.2.1

# create the db tables
cat <<EOPY | python -
from prop_xfer.app import app, db
with app.app_context():
    db.create_all()
EOPY
EOSU

echo "workon venv; cd /vagrant; echo \"To Run: 'python prop_xfer/app.py'\"" >> /home/vagrant/.bashrc
