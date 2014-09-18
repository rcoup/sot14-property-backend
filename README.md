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

Usual git clone, virtualenv, requirements.txt, db-creation (Postgresql).

If you're starting out, you need to:
* Set `DATABASE_URL` in your environment
* Make sure your database is PostGIS-enabled (`CREATE EXTENSION postgis;`)
* Run `prop_xfer.app.app.db.create_all()` first to setup the tables
* Run `scripts/populate_db.py` to populate the DB
* Run `prop_xfer/app.py` to run the web service
