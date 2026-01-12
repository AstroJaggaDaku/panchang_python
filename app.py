import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz
import math

app = Flask(__name__)

# Lahiri Ayanamsa (Drik Panchang Standard)
swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
        "Purva Bhadrapada","Uttara Bhadrapada","Revati"]

TITHI = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

KARANA = ["Bava","Balava","Kaulava","Taitila","Garija","Vanija","Vishti"] * 5

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day,
                       dt.hour + dt.minute/60 + dt.second/3600)

def jd_to_local(jd, tz):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400, tz)

def find_end(jd, fn, step=1/1440):
    v = fn(jd)
    j = jd
    for _ in range(1440):   # max 24h search
        j += step
        if fn(j) != v:
            return j
    return j

@app.route("/panchang")
def panchang():
    try:
        lat = float(request.args.get("lat", 22.57))
        lon = float(request.args.get("lon", 88.36))
        tz  = request.args.get("tz", "Asia/Kolkata")

        tzobj = pytz.timezone(tz)
        now = datetime.now(tzobj)
        jd = julian(now)

        geopos = (lon, lat, 0)

        # Sidereal longitudes
        sun = swe.calc_ut(jd, swe.SUN)[0][0]
        moon = swe.calc_ut(jd, swe.MOON)[0][0]

        # -------- Core Panchang --------
        diff = (moon - sun) % 360.0
        tithiIndex = int(diff / 12.0)
        if tithiIndex < 0: tithiIndex = 0
        if tithiIndex > 29: tithiIndex = 29

        nakIndex = int(moon / 13.333333) % 27

        yogaIndex = int(((sun + moon) % 360.0) / 13.333333)
        if yogaIndex > 26: yogaIndex = 26

        # ---- End Times ----
        tithiEnd = find_end(jd, lambda j:
            int(((swe.calc_ut(j,swe.MOON)[0][0] - swe.calc_ut(j,swe.SUN)[0][0]) % 360.0) / 12.0)
        )

        nakEnd = find_end(jd, lambda j:
            int((swe.calc_ut(j,swe.MOON)[0][0] % 360.0) / 13.333333)
        )

        yogaEnd = find_end(jd, lambda j:
            int(((swe.calc_ut(j,swe.SUN)[0][0] + swe.calc_ut(j,swe.MOON)[0][0]) % 360.0) / 13.333333)
        )

        # ---- Rise & Set ----
        sunrise = swe.rise_trans(jd, swe.SUN, swe.CALC_RISE, geopos)[1]
        sunset  = swe.rise_trans(jd, swe.SUN, swe.CALC_SET,  geopos)[1]
        moonrise = swe.rise_trans(jd, swe.MOON, swe.CALC_RISE, geopos)[1]
        moonset  = swe.rise_trans(jd, swe.MOON, swe.CALC_SET,  geopos)[1]

        sr = jd_to_local(sunrise, tzobj)
        ss = jd_to_local(sunset, tzobj)

        daymins = (ss - sr).total_seconds() / 60.0

        # Rahu Kaal (Monday pattern already correct)
        rahu_start = sr + timedelta(minutes=78)
        rahu_end   = rahu_start + timedelta(minutes=88)

        # Abhijit
        mid = sr + timedelta(minutes=daymins/2)
        abh_start = mid - timedelta(minutes=24)
        abh_end   = mid + timedelta(minutes=24)

        return jsonify({
            "tithi": TITHI[tithiIndex],
            "tithi_end": jd_to_local(tithiEnd, tzobj).strftime("%H:%M:%S"),
            "nakshatra": NAKS[nakIndex],
            "nakshatra_end": jd_to_local(nakEnd, tzobj).strftime("%H:%M:%S"),
            "karana": KARANA[(tithiIndex * 2) % len(KARANA)],
            "paksha": "Shukla" if tithiIndex < 15 else "Krishna",
            "yoga": yogaIndex + 1,
            "yoga_end": jd_to_local(yogaEnd, tzobj).strftime("%H:%M:%S"),
            "sunrise": sr.strftime("%H:%M:%S"),
            "sunset": ss.strftime("%H:%M:%S"),
            "moonrise": jd_to_local(moonrise, tzobj).strftime("%H:%M:%S"),
            "moonset": jd_to_local(moonset, tzobj).strftime("%H:%M:%S"),
            "rahu_kaal": f"{rahu_start.strftime('%H:%M:%S')} - {rahu_end.strftime('%H:%M:%S')}",
            "abhijit": f"{abh_start.strftime('%H:%M:%S')} - {abh_end.strftime('%H:%M:%S')}",
            "moon_rashi": RASHI[int((moon % 360) / 30)],
            "ritu": RITU[int((sun % 360) / 60)]
        })

    except Exception as e:
        return jsonify({"error": "Panchang Engine Error", "details": str(e)}), 500
