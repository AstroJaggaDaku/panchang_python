import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz, math

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

TITHI = ["Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami",
         "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
         "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami",
         "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"]

KARANA = ["Bava","Balava","Kaulava","Taitila","Garija","Vanija","Vishti"] * 5

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)

def find_end(jd, fn, step=1/1440):
    v = fn(jd)
    j = jd
    while True:
        j += step
        if fn(j) != v:
            return j

@app.route("/panchang")
def panchang():
    tz = request.args.get("tz","Asia/Kolkata")
    tzobj = pytz.timezone(tz)
    now = datetime.now(tzobj)
    jd = julian(now)

    sun = swe.calc_ut(jd,swe.SUN)[0][0]
    moon = swe.calc_ut(jd,swe.MOON)[0][0]

    diff = (moon - sun) % 360
    tithiIndex = min(29,int(diff/12))
    nakIndex = int(moon/13.333333)%27
    yogaIndex = int(((sun+moon)%360)/13.333333)

    tithiEnd = find_end(jd, lambda j: int(((swe.calc_ut(j,swe.MOON)[0][0] - swe.calc_ut(j,swe.SUN)[0][0])%360)/12))
    nakEnd = find_end(jd, lambda j: int(swe.calc_ut(j,swe.MOON)[0][0]/13.333333))
    yogaEnd = find_end(jd, lambda j: int(((swe.calc_ut(j,swe.SUN)[0][0]+swe.calc_ut(j,swe.MOON)[0][0])%360)/13.333333))

    sunrise = swe.rise_trans(jd, swe.SUN, swe.CALC_RISE)[1]
    sunset  = swe.rise_trans(jd, swe.SUN, swe.CALC_SET)[1]

    moonrise = swe.rise_trans(jd, swe.MOON, swe.CALC_RISE)[1]
    moonset  = swe.rise_trans(jd, swe.MOON, swe.CALC_SET)[1]

    sr = datetime.fromtimestamp((sunrise-2440587.5)*86400, tzobj)
    ss = datetime.fromtimestamp((sunset-2440587.5)*86400, tzobj)

    daymins = (ss-sr).seconds/60
    rahu = (sr+timedelta(minutes=78), sr+timedelta(minutes=166))
    abhijit = (sr+timedelta(minutes=daymins/2-24), sr+timedelta(minutes=daymins/2+24))

    return jsonify({
        "tithi":TITHI[tithiIndex],
        "tithi_end":str(datetime.fromtimestamp((tithiEnd-2440587.5)*86400, tzobj).time()),
        "nakshatra":NAKS[nakIndex],
        "nakshatra_end":str(datetime.fromtimestamp((nakEnd-2440587.5)*86400, tzobj).time()),
        "karana":KARANA[tithiIndex*2 % len(KARANA)],
        "paksha":"Shukla" if tithiIndex<15 else "Krishna",
        "yoga":yogaIndex+1,
        "yoga_end":str(datetime.fromtimestamp((yogaEnd-2440587.5)*86400, tzobj).time()),
        "sunrise":sr.time().isoformat(),
        "sunset":ss.time().isoformat(),
        "rahu_kaal":f"{rahu[0].time()} - {rahu[1].time()}",
        "abhijit":f"{abhijit[0].time()} - {abhijit[1].time()}",
        "moon_rashi":RASHI[int(moon/30)%12],
        "ritu":RITU[int(sun/60)%6]
    })
