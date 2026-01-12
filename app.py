import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz
import math

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# -------- TABLES --------

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

TITHI = [
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

KARANA = ["Bava","Balava","Kaulava","Taitila","Garija","Vanija","Vishti"] * 5
RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]
AMANTA = ["Chaitra","Vaisakha","Jyeshtha","Ashadha","Shravana","Bhadrapada","Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]

# ---- Crash-safe accessor ----
def safe(arr, i):
    return arr[int(i) % len(arr)]

# ---- Utils ----
def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)

def jd_to_local(jd,tz):
    return datetime.fromtimestamp((jd-2440587.5)*86400,tz)

def find_end(jd, fn):
    base = fn(jd)
    j = jd
    for _ in range(1440):
        j += 1/1440
        if fn(j)!=base:
            return j
    return j

# ---- API ----
@app.route("/panchang")
def panchang():
    try:
        lat=float(request.args.get("lat",22.57))
        lon=float(request.args.get("lon",88.36))
        tz=request.args.get("tz","Asia/Kolkata")

        tzobj=pytz.timezone(tz)
        now=datetime.now(tzobj)
        jd=julian(now)
        geopos=(lon,lat,0)

        sun=swe.calc_ut(jd,swe.SUN)[0][0]%360
        moon=swe.calc_ut(jd,swe.MOON)[0][0]%360

        diff=(moon-sun)%360
        tithiIndex=int(diff/12)
        nakIndex=int(moon/13.333333)
        yogaIndex=int((sun+moon)%360/13.333333)

        tithiEnd=find_end(jd,lambda j:int(((swe.calc_ut(j,swe.MOON)[0][0]-swe.calc_ut(j,swe.SUN)[0][0])%360)/12))
        nakEnd=find_end(jd,lambda j:int((swe.calc_ut(j,swe.MOON)[0][0]%360)/13.333333))
        yogaEnd=find_end(jd,lambda j:int(((swe.calc_ut(j,swe.SUN)[0][0]+swe.calc_ut(j,swe.MOON)[0][0])%360)/13.333333))

        sunrise=swe.rise_trans(jd,swe.SUN,swe.CALC_RISE,geopos)[1][0]
        sunset=swe.rise_trans(jd,swe.SUN,swe.CALC_SET,geopos)[1][0]
        moonrise=swe.rise_trans(jd,swe.MOON,swe.CALC_RISE,geopos)[1][0]
        moonset=swe.rise_trans(jd,swe.MOON,swe.CALC_SET,geopos)[1][0]

        sr=jd_to_local(sunrise,tzobj)
        ss=jd_to_local(sunset,tzobj)

        sun_rashi=int(sun/30)
        moon_rashi=int(moon/30)

        return jsonify({
            "tithi": safe(TITHI,tithiIndex),
            "tithi_end": jd_to_local(tithiEnd,tzobj).strftime("%H:%M:%S"),
            "nakshatra": safe(NAKS,nakIndex),
            "nakshatra_end": jd_to_local(nakEnd,tzobj).strftime("%H:%M:%S"),
            "karana": safe(KARANA,tithiIndex*2),
            "paksha":"Shukla" if tithiIndex<15 else "Krishna",
            "yoga": yogaIndex+1,
            "yoga_end": jd_to_local(yogaEnd,tzobj).strftime("%H:%M:%S"),
            "sunrise": sr.strftime("%H:%M:%S"),
            "sunset": ss.strftime("%H:%M:%S"),
            "moonrise": jd_to_local(moonrise,tzobj).strftime("%H:%M:%S"),
            "moonset": jd_to_local(moonset,tzobj).strftime("%H:%M:%S"),
            "moon_rashi": safe(RASHI,moon_rashi),
            "ritu": safe(RITU,int(sun/60)),
            "amanta_month": safe(AMANTA,sun_rashi)
        })

    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500
