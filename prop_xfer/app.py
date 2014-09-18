import datetime
import os
import re

from flask import Flask, jsonify
from flask.ext.compress import Compress
from geoalchemy2.shape import from_shape
from shapely.geometry import box, MultiPolygon

from prop_xfer.models import db, Transfer


app = Flask("prop_xfer")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db.init_app(app)
Compress(app)



@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/week/<date>', defaults={'bounds': None})
@app.route('/week/<date>/<bounds>')
def week_data(date, bounds):
    try:
        week_start = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError as e:
        r = jsonify({"error": str(e)})
        r.status_code = 400
        return r

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

    query = Transfer.query.filter_by(week_start=week_start)
    if bounds:
        query = query.filter(Transfer.location.ST_Intersects(from_shape(bounds, 4326)))

    features = []
    for transfer in query:
        features.append(transfer.as_geojson())

    return jsonify({
        "type": "FeatureCollection",
        "features": features,
    })

if __name__ == '__main__':
    app.run(debug=True)
