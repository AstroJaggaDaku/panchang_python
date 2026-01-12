import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------- TABLES ----------------

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
        "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
        "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

TITHI = [
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]

# Rahu/Yama/Gulika – Drik Panchang standard
RAHU_SEG=[1,6,4,5,3,2,0]
YAMA_SEG=[4,3,2,1,0,6,5]
GULI_SEG=[6,5,4,3,2,1,0]

YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
         "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata",
         "Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]

# ---------------- UTILS ----------------

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60)

def jd_to_local(jd,tz):
    return datetime.fromtimestamp((jd-2440587.5)*86400,tz)

def muhurta(sr,daymins,seg):
    return (
      sr+timedelta(minutes=seg*daymins/8),
      sr+timedelta(minutes=(seg+1)*daymins/8)
    )

# Core Panchang Calculator
def calc_panchang(date, lat, lon, tz):
    tzobj=pytz.timezone(tz)
    base=tzobj.localize(datetime(date.year,date.month,date.day,6,0,0))
    jd0=julian(base)
    geopos=(lon,lat,0)

    sunrise=swe.rise_trans(jd0,swe.SUN,swe.CALC_RISE,geopos)[1][0]
    sunset =swe.rise_trans(jd0,swe.SUN,swe.CALC_SET,geopos)[1][0]

    sr=jd_to_local(sunrise,tzobj)
    ss=jd_to_local(sunset,tzobj)
    daymins=(ss-sr).total_seconds()/60

    jd=julian(sr)

    sun=swe.calc_ut(jd,swe.SUN)[0][0]%360
    moon=swe.calc_ut(jd,swe.MOON)[0][0]%360

    diff=(moon-sun)%360
    tithiIndex=int(diff/12)
    nakIndex=int(moon/13.333333)
    yogaIndex=int((sun+moon)%360/13.333333)

    wd=sr.weekday()

    rahu_s,rahu_e=muhurta(sr,daymins,RAHU_SEG[wd])
    yama_s,yama_e=muhurta(sr,daymins,YAMA_SEG[wd])
    gul_s ,gul_e =muhurta(sr,daymins,GULI_SEG[wd])

    mid=sr+timedelta(minutes=daymins/2)
    abh_s=mid-timedelta(minutes=24)
    abh_e=mid+timedelta(minutes=24)

    return {
      "date":sr.strftime("%Y-%m-%d"),
      "day":sr.strftime("%A"),
      "tithi":TITHI[tithiIndex],
      "nakshatra":NAKS[nakIndex],
      "yoga":YOGAS[yogaIndex],
      "paksha":"Krishna" if tithiIndex>=15 else "Shukla",
      "sunrise":sr.strftime("%H:%M:%S"),
      "sunset":ss.strftime("%H:%M:%S"),
      "moon_rashi":RASHI[int(moon/30)],
      "rahu_kaal":f"{rahu_s.strftime('%H:%M:%S')} - {rahu_e.strftime('%H:%M:%S')}",
      "yamaganda":f"{yama_s.strftime('%H:%M:%S')} - {yama_e.strftime('%H:%M:%S')}",
      "gulika":f"{gul_s.strftime('%H:%M:%S')} - {gul_e.strftime('%H:%M:%S')}",
      "abhijit":f"{abh_s.strftime('%H:%M:%S')} - {abh_e.strftime('%H:%M:%S')}"
    }

# ---------------- API ----------------

@app.route("/panchang")
def daily():
    lat=float(request.args.get("lat",22.57))
    lon=float(request.args.get("lon",88.36))
    tz=request.args.get("tz","Asia/Kolkata")
    date=request.args.get("date")

    if date:
        y,m,d=map(int,date.split("-"))
        dt=datetime(y,m,d)
    else:
        dt=datetime.now(pytz.timezone(tz))

    return jsonify(calc_panchang(dt,lat,lon,tz))

@app.route("/panchang/month")
def month():
    lat=float(request.args.get("lat",22.57))
    lon=float(request.args.get("lon",88.36))
    tz=request.args.get("tz","Asia/Kolkata")
    year=int(request.args.get("year"))
    month=int(request.args.get("month"))

    days=[]
    d=datetime(year,month,1)
    while d.month==month:
        days.append(calc_panchang(d,lat,lon,tz))
        d+=timedelta(days=1)

    return jsonify(days)

@app.route("/panchang/festivals")
def festivals():
    lat=float(request.args.get("lat",22.57))
    lon=float(request.args.get("lon",88.36))
    tz=request.args.get("tz","Asia/Kolkata")
    year=int(request.args.get("year"))
    month=int(request.args.get("month"))

    out=[]
    d=datetime(year,month,1)
    while d.month==month:
        p=calc_panchang(d,lat,lon,tz)
        if p["tithi"] in ["Amavasya","Purnima","Ekadashi","Chaturthi"]:
            out.append(p)
        d+=timedelta(days=1)

    return jsonify(out)
