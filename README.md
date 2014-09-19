## Summer of Tech 2014 Auckland HackFest - Property Transfer Map Backend

A simple backend web service for returning where properties changed hands
based on data from the LINZ Data Service.

## API

### `/week/YYYY-MM-DD`

Returns a GeoJSON FeatureCollection of property titles created or updated
during the week starting `YYYY-MM-DD`. ProTip: Use a Saturday after 2012-05-12 :)

### `/week/YYYY-MM-DD/west,south,east,north`

Returns a GeoJSON FeatureCollection of property titles created or updated
during the week starting `YYYY-MM-DD` that are spatially located in the bounds
specified by `west,south,east,north` (longitudes/latitudes in decimal degreees).

## Developing

* Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) and [Vagrant](https://www.vagrantup.com/downloads.html)
* `git clone` this repository.
* `vagrant up` to build a dev environment
* `vagrant ssh` then `python prop_xfer/app.py` to run the backend.
* Head to http://localhost:5000/
