import datetime
import os
import re
import hashlib, json
from flask import Flask, jsonify, send_from_directory
from flask.ext.compress import Compress
from geoalchemy2.shape import from_shape
from shapely.geometry import box, MultiPolygon
from prop_xfer.models import db, Transfer

app = Flask("prop_xfer", static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db.init_app(app)
Compress(app)
NO_CACHE = bool(int(os.environ.get("NO_CACHE", "0")))
# print bool(os.environ.get("NO_CACHE", "0"))

cache_folder = os.path.dirname(os.path.realpath(__file__)) + '/cache'

#Creates cache directory
if not os.path.exists(cache_folder):
    print 'Creating cache directory...'
    os.makedirs(cache_folder)

def clear_cache():
    folder = cache_folder
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception, e:
            print e


@app.route('/')
def home():
    return app.send_static_file("index.html")

@app.route('/stats', defaults={'bounds': None})
@app.route('/stats/', defaults={'bounds': None})
@app.route('/stats/<bounds>')
def stats(bounds):

    cache_location = cache_folder + '/' + hashlib.md5('stats/' + str(bounds)).hexdigest() + '.json.cache'
    if os.path.isfile(cache_location) and not NO_CACHE:
        with open(cache_location) as r:
            data = jsonify(json.loads(r.read()))
            return data
    else:
        if bounds:
            try:
                m = re.match(r'((-?\d+(?:\.\d+)?),){3}(-?\d+(\.\d+)?)$', bounds)
                if not m:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")
                w,s,e,n = map(float, bounds.split(','))
                if w < -180 or w > 180 or e < -180 or e > 180:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")
                elif s < -90 or s > 90 or n < -90 or n > 90 or s > n:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")

                if e < w:
                    bounds = MultiPolygon([box(w, s, 180, n), box(-180, s, e, n)])
                else:
                    bounds = MultiPolygon([box(w, s, e, n)])
            except ValueError as e:
                r = jsonify({"error": str(e)})
                r.status_code = 400
                return r
        dates = {}
        query = Transfer.query.distinct(Transfer.week_start)
        for date in query:
            q = Transfer.query.filter_by(week_start=date.return_date())
            if bounds:
                dates.update({str(date.return_date()) : q.filter(Transfer.location.ST_Intersects(from_shape(bounds, 4326))).count()})
            else:
                dates.update({str(date.return_date()) : q.count()})

        if not NO_CACHE:
            print "Cahing json: ", cache_location
            with open(cache_location, 'w') as w:
                w.write(json.dumps(dates))

        return jsonify(dates)
       

@app.route('/week/<date>', defaults={'bounds': None})
@app.route('/week/<date>/', defaults={'bounds': None})
@app.route('/week/<date>/<bounds>')
def week_data(date, bounds):
    """
    Query Transfer data for a week, optionally spatially filtered.
    Returns a GeoJSON FeatureCollection.
    """
    #Creates md5 link to cache file
    cache_location = cache_folder + '/' + hashlib.md5('week/' + str(date) + '/' + str(bounds)).hexdigest() + '.json.cache'
    if os.path.isfile(cache_location) and not NO_CACHE:
        with open(cache_location) as r:
            data = jsonify(json.loads(r.read()))
            return data
    else:
        try:
            # week should be in ISO YYYY-MM-DD format
            week_start = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError as e:
            r = jsonify({"error": str(e)})
            r.status_code = 400
            return r

        if bounds:
            # Optionally, filter the results spatially
            # west,south,east,north in degrees (latitude/longitude)
            try:
                m = re.match(r'((-?\d+(?:\.\d+)?),){3}(-?\d+(\.\d+)?)$', bounds)
                if not m:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")
                w,s,e,n = map(float, bounds.split(','))
                if w < -180 or w > 180 or e < -180 or e > 180:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")
                elif s < -90 or s > 90 or n < -90 or n > 90 or s > n:
                    raise ValueError("Bounds should be longitudes/latitudes in west,south,east,north order")

                if e < w:
                    bounds = MultiPolygon([box(w, s, 180, n), box(-180, s, e, n)])
                else:
                    bounds = MultiPolygon([box(w, s, e, n)])
            except ValueError as e:
                r = jsonify({"error": str(e)})
                r.status_code = 400
                return r

        # Filter the transfers - the DB query happens here
        query = Transfer.query.filter_by(week_start=week_start)
        if bounds:
            query = query.filter(Transfer.location.ST_Intersects(from_shape(bounds, 4326)))

        query = query.limit(2000)

        features = []
        for transfer in query:
            features.append(transfer.as_geojson())

        # Caching data
        if not NO_CACHE:
            print "Cahing json: ", cache_location
            with open(cache_location, 'w') as w:
                w.write(json.dumps({"type": "FeatureCollection","features": features}))

        # Format the response as a GeoJSON FeatureCollection
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })

@app.route('/static/<path:path>')
def static_proxy(path):
    return app.send_static_file(path)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
