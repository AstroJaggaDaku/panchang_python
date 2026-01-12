import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)

# Lahiri Ayanamsa (Drik Panchang standard)
swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu",
    "Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra",
    "Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha",
    "Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# 30 Tithi (15 Shukla + 15 Krishna)
TITHI = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

def julian(dt):
    return swe.julday(
        dt.year, dt.month, dt.day,
        dt.hour + dt.minute/60 + dt.second/3600
    )

@app.route("/panchang")
def panchang():
    try:
        lat = float(request.args.get("lat",22.57))
        lon = float(request.args.get("lon",88.36))
        tz  = request.args.get("tz","Asia/Kolkata")

        tzobj = pytz.timezone(tz)
        now = datetime.now(tzobj)

        jd = julian(now)

        # Swiss Ephemeris Sidereal Positions
        sun = swe.calc_ut(jd, swe.SUN)[0][0]
        moon = swe.calc_ut(jd, swe.MOON)[0][0]

        # ---------- DRIC PANCHANG CORE ----------
        diff = (moon - sun) % 360.0

        # Tithi (safe clamp)
        tithiIndex = int(diff / 12.0)
        if tithiIndex < 0: tithiIndex = 0
        if tithiIndex > 29: tithiIndex = 29

        # Nakshatra (safe clamp)
        nakIndex = int(moon / 13.333333) % 27

        # Yoga
        yogaIndex = int(((sun + moon) % 360.0) / 13.333333)
        if yogaIndex < 0: yogaIndex = 0
        if yogaIndex > 26: yogaIndex = 26

        # Paksha
        paksha = "Shukla" if tithiIndex < 15 else "Krishna"

        return jsonify({
            "engine": "Swiss Ephemeris + Lahiri (Drik Panchang)",
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "panchang":{
                "tithi": TITHI[tithiIndex],
                "paksha": paksha,
                "nakshatra": NAKS[nakIndex],
                "yoga": yogaIndex + 1,
                "sun_longitude": round(sun,6),
                "moon_longitude": round(moon,6)
            }
        })

    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500
