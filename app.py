import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
TITHI = ["Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima","Amavasya"]

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)

@app.route("/panchang")
def panchang():
    lat = float(request.args.get("lat",22.57))
    lon = float(request.args.get("lon",88.36))
    tz  = request.args.get("tz","Asia/Kolkata")

    tzobj = pytz.timezone(tz)
    now = datetime.now(tzobj)
    j = julian(now)

    sun = swe.calc_ut(j, swe.SUN)[0][0]
    moon = swe.calc_ut(j, swe.MOON)[0][0]

    diff = (moon - sun + 360) % 360
    tithiIndex = int(diff / 12)
    nakIndex = int(moon / 13.333333)
    yogaIndex = int(((sun + moon) % 360) / 13.333333)

    return jsonify({
        "panchang": {
            "tithi": TITHI[tithiIndex],
            "nakshatra": NAKS[nakIndex],
            "yoga": yogaIndex + 1,
            "sun_longitude": sun,
            "moon_longitude": moon
        }
    })
