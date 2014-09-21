#!/usr/bin/env python

"""
Pull data down from the LINZ Data Service and populate the Transfers table.

We get data from https://data.linz.govt.nz/layer/804-nz-property-titles/
and use the WFS Changeset service to request data each week from May 2012.

Deletes all records and re-populates the database from scratch.

You need a LINZ Data Service API Key to give this script.

If you're starting out, you need to:
* Make sure your database is PostGIS-enabled ('CREATE EXTENSION postgis;')
* Run app.db.create_all() first to setup the tables
* Run this.
"""

import datetime
import json
import os
import sys
import re

import dateutil.parser
from dateutil.relativedelta import relativedelta, SA
from dateutil.tz import tzutc
from geoalchemy2.shape import from_shape
import psycopg2.extensions
import requests
from shapely.geometry import shape

from prop_xfer.app import app, db, clear_cache
from prop_xfer.models import Transfer



BASE_LAYER_URL = "https://data.linz.govt.nz/services/wfs/layer-805-changeset?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&typeNames=layer-805-changeset&viewparams=from:%s;to:%s&outputFormat=application/json&exceptions=application/json&srsName=EPSG:4326"
START_DATE = os.environ.get("PX_START", "2013-05-17T00:00:00Z")  #Thursday
DEBUG = int(os.environ.get("PX_DEBUG", "0"))

def main(api_key):
    req_headers = {
        'Authorization': "key %s" % sys.argv[1],
    }

    with app.app_context():
        # Weeks are Saturday to Saturday
        # Queries are Thursday to Thursday
        clear_cache()
        date_end = datetime.datetime.now(tzutc())
        query_date_start = dateutil.parser.parse(START_DATE)
        query_date_end = query_date_start + relativedelta(weeks=1)

        # nuke any existing data
        week_start = query_date_start + relativedelta(weekday=SA(-1))
        print Transfer
        Transfer.query.filter(Transfer.week_start >= week_start).delete()

        while query_date_end < date_end:
            week_start = query_date_start + relativedelta(weekday=SA(-1))
            week_end = query_date_start + relativedelta(weekday=SA(+1))

            if DEBUG:
                print "Query", query_date_start, query_date_end, "week", week_start, week_end

            # Construct the LDS changeset url for the week
            url = BASE_LAYER_URL % (query_date_start.isoformat("T").replace("+00:00", "Z"), query_date_end.isoformat("T").replace("+00:00", "Z"))
            print url
            if DEBUG >= 2:
                print url

            r = requests.get(url, headers=req_headers)
            if DEBUG >= 4:
                print r.status
                print r.text

            r.raise_for_status()

            data = r.json()
            print "%s -> %s: %d records" % (week_start.date(), week_end.date(), len(data['features']))
            if DEBUG >= 3:
                print json.dumps(data, indent=2)

            def create_xfers(features):
                # generator for Transfer objects
                for feature in features:
                    if DEBUG >= 2:
                        print json.dumps(feature, indent=2)

                    props = feature['properties']
                    if props['__change__'] == 'DELETE':
                        # ignore DELETEs since title splits/etc will show up as INSERTs too.
                        continue

                    action = 'new' if props['__change__'] == 'INSERT' else 'existing'

                    # use a point within the title (centroid normally)
                    if not feature['geometry']:
                        continue

                    location = from_shape(shape(feature['geometry']).representative_point(), srid=4326)
                    owners = props['owners']
                    #DEV SECTION#
                    owner_type = ''
                    if bool(re.search(r"\bHer Majesty The Queen\b", props['owners'], re.I)) \
                            or bool(re.search(r"\bCouncil\b", props['owners'], re.I)):  
                        owner_type = 'govt'

                    elif bool(re.search(r"\bLimited\b", props['owners'], re.I)) \
                            or bool(re.search(r"\bIncorporated\b", props['owners'], re.I)):
                        owner_type = 'company'
                    else:
                        owner_type = 'private'


                    # create our Transfer object
                    transfer = Transfer(props['title_no'], location, action, week_start, owners, owner_type)
                    yield transfer

            # Insert all the Transfers in one go
            db.session.add_all((t for t in create_xfers(data['features'])))
            # One transaction per-week
            db.session.commit()

            # loop around again
            query_date_start += relativedelta(weeks=1)
            query_date_end = query_date_start + relativedelta(weeks=1)
            if DEBUG:
                break

        # Drama to run VACUUM ANALYZE
        conn = db.engine.connect()
        conn.connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        conn.execute('VACUUM ANALYZE;')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "Usage: %s APIKEY\n\nSet PX_START_DATE=YYYY-MM-DD or PX_DEBUG=n if you want"
        sys.exit(2)

    main(sys.argv[1])
