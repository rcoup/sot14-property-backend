#!/usr/bin/env python

import datetime
import json
import sys

import dateutil.parser
from dateutil.relativedelta import relativedelta, SA
from dateutil.tz import tzutc
from geoalchemy2.shape import from_shape
import psycopg2.extensions
import requests
from shapely.geometry import shape

from prop_xfer.app import db
from prop_xfer.models import Transfer


BASE_LAYER_URL = "https://data.linz.govt.nz/services/wfs/layer-804-changeset?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&typeNames=layer-804-changeset&viewparams=from:%s;to:%s&outputFormat=application/json&exceptions=application/json&srsName=EPSG:4326"
START_DATE = "2012-05-17T00:00:00Z"

def main(api_key):
    req_headers = {
        'Authorization': "key %s" % sys.argv[1],
    }

    # nuke any existing data
    Transfer.query.delete()

    # Weeks are Saturday to Saturday
    # Queries are Thursday to Thursday
    date_end = datetime.datetime.now(tzutc())
    query_date_start = dateutil.parser.parse(START_DATE)
    query_date_end = query_date_start + relativedelta(weeks=1)

    while query_date_end < date_end:
        week_start = query_date_start + relativedelta(weekday=SA(-1))
        week_end = query_date_start + relativedelta(weekday=SA(+1))

        #print "Query", query_date_start, query_date_end, "week", week_start, week_end

        # Construct the LDS changeset url for the week
        url = BASE_LAYER_URL % (query_date_start.isoformat("T").replace("+00:00", "Z"), query_date_end.isoformat("T").replace("+00:00", "Z"))
        r = requests.get(url, headers=req_headers)
        r.raise_for_status()

        data = r.json()
        print "%s -> %s: %d records" % (week_start.date(), week_end.date(), len(data['features']))
        # print json.dumps(data, indent=2)

        def create_xfers(features):
            # generator for Transfer objects
            for feature in features:
                props = feature['properties']
                if props['__change__'] == 'DELETE':
                    # ignore DELETEs since title splits/etc will show up as INSERTs too.
                    continue

                #print json.dumps(feature, indent=2)
                action = 'new' if props['__change__'] == 'INSERT' else 'existing'
                # use a point within the title (centroid normally)
                location = from_shape(shape(feature['geometry']).representative_point(), srid=4326)
                # create our Transfer object
                transfer = Transfer(props['title_no'], location, action, week_start)
                yield transfer

        # Insert all the Transfers in one go
        db.session.add_all((t for t in create_xfers(data['features'])))
        break

        # loop around again
        query_date_start += relativedelta(weeks=1)
        query_date_end = query_date_start + relativedelta(weeks=1)

    db.session.commit()

    # Drama to run VACUUM ANALYZE
    conn = db.engine.connect()
    conn.connection.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    conn.execute('VACUUM ANALYZE;')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: %s APIKEY"
        sys.exit(2)

    main(sys.argv[1])
