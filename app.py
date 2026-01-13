import os
import swisseph as swe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz
import math

# ---------------- Swiss Ephemeris ----------------
if os.path.exists("/usr/share/ephe"):
    swe.set_ephe_path("/usr/share/ephe")

swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------- Flask ----------------
app = Flask(__name__)
CORS(app)

# ---------------- Tables ----------------

TITHI = [
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

KARANA = (
 ["Kimstughna"] +
 ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"] * 8 +
 ["Shakuni","Chatushpada","Naga"]
)

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya",
        "Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
        "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
        "Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
         "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi",
         "Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla",
         "Brahma","Indra","Vaidhriti"]

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
         "Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]

AMANTA = ["Chaitra","Vaisakha","Jyeshtha","Ashadha","Shravana","Bhadrapada",
          "Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]

RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

RAHU=[8,2,7,5,6,4,3]
YAMA=[5,4,3,2,1,7,6]
GULI=[7,6,5,4,3,2,1]

# ---------------- Core ----------------

def jd(dt):
    return swe.julday(dt.year, dt.month, dt.day,
        dt.hour + dt.minute/60 + dt.second/3600)

def from_jd(j, tz):
    return datetime.fromtimestamp((j - 2440587.5) * 86400, tz)

def calc(j, p):
    return swe.calc_ut(j, p, swe.FLG_SIDEREAL | swe.FLG_SWIEPH)[0][0] % 360

def sun_moon(j):
    return calc(j, swe.SUN), calc(j, swe.MOON)

def ang(a,b):
    return (a-b) % 360

# ---------------- AstroSage-style Sunrise ----------------

def rise(j, planet, flag, geo):
    r = swe.rise_trans(j, planet, flag, geo, atpress=0, attemp=0)
    return r[1][0]

def sunrise(dt,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(dt.year,dt.month,dt.day,0))
    for h in [6,7,5]:
        try:
            return from_jd(rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_RISE,geo),tz)
        except:
            pass
    raise Exception("Sunrise fail")

def sunset(dt,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(dt.year,dt.month,dt.day,12))
    for h in [0,1,-1]:
        try:
            return from_jd(rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_SET,geo),tz)
        except:
            pass
    raise Exception("Sunset fail")

# ---------------- AstroSage Event Solver ----------------

def solve(j0,target,fn):
    j=j0
    step=0.02
    prev=(fn(j)-target)%360
    for _ in range(3000):
        j+=step
        cur=(fn(j)-target)%360
        if prev>300 and cur<60:
            lo=j-step; hi=j; break
        prev=cur
    for _ in range(50):
        mid=(lo+hi)/2
        if (fn(mid)-target)%360 < 180: hi=mid
        else: lo=mid
    return hi

# ---------------- Panchang ----------------

def panchang(dt,lat,lon,tzname):
    tz=pytz.timezone(tzname)

    sr=sunrise(dt,lat,lon,tz)
    ss=sunset(dt,lat,lon,tz)
    j0=jd(sr)

    sun,moon=sun_moon(j0)
    diff=ang(moon,sun)

    t=int(diff/12)
    n=int(moon/13.3333333333)
    y=int(((sun+moon)%360)/13.3333333333)

    t_end=solve(j0,(t+1)*12,lambda j:ang(calc(j,swe.MOON),calc(j,swe.SUN)))
    n_end=solve(j0,(n+1)*13.3333333333,lambda j:calc(j,swe.MOON))
    y_end=solve(j0,(y+1)*13.3333333333,lambda j:(calc(j,swe.SUN)+calc(j,swe.MOON))%360)

    kar = "Kimstughna" if t==0 and diff<6 else KARANA[int((diff-6)/6)%60]

    ama=solve(j0,0,lambda j:ang(calc(j,swe.MOON),calc(j,swe.SUN)))
    sun_ama=calc(ama,swe.SUN)
    amanta=AMANTA[int(sun_ama//30)%12]
    purni=AMANTA[(int(sun_ama//30)+1)%12]

    dur=ss-sr
    mins=dur.total_seconds()/60
    wd=(sr.weekday()+1)%7
    def seg(n): return (sr+timedelta(minutes=(n-1)*mins/8),sr+timedelta(minutes=n*mins/8))

    rahu=seg(RAHU[wd]); yama=seg(YAMA[wd]); guli=seg(GULI[wd])
    abh=(sr+dur*(7/15),sr+dur*(8/15))

    return {
      "date": sr.strftime("%Y-%m-%d"),
      "day": sr.strftime("%A"),
      "tithi": TITHI[t],
      "tithi_end": from_jd(t_end,tz).strftime("%H:%M:%S"),
      "nakshatra": NAKS[n],
      "nakshatra_end": from_jd(n_end,tz).strftime("%H:%M:%S"),
      "yoga": YOGAS[y],
      "yoga_end": from_jd(y_end,tz).strftime("%H:%M:%S"),
      "karana": kar,
      "paksha": "Krishna" if t>=15 else "Shukla",
      "sunrise": sr.strftime("%H:%M:%S"),
      "sunset": ss.strftime("%H:%M:%S"),
      "moon_sign": RASHI[int(moon//30)%12],
      "amanta_month": amanta,
      "purnimanta_month": purni,
      "ritu": RITU[int(sun//60)%6],
      "vikram_samvat": dt.year+57,
      "shaka_samvat": dt.year-78,
      "kali_samvat": dt.year+3101,
      "rahu_kalam": f"{rahu[0].strftime('%H:%M:%S')} - {rahu[1].strftime('%H:%M:%S')}",
      "yamaganda": f"{yama[0].strftime('%H:%M:%S')} - {yama[1].strftime('%H:%M:%S')}",
      "gulika": f"{guli[0].strftime('%H:%M:%S')} - {guli[1].strftime('%H:%M:%S')}",
      "abhijit": f"{abh[0].strftime('%H:%M:%S')} - {abh[1].strftime('%H:%M:%S')}"
    }

# ---------------- API ----------------

@app.route("/panchang")
def api():
    tzname=request.args.get("tz","Asia/Kolkata")
    lat=float(request.args.get("lat",22.5726))
    lon=float(request.args.get("lon",88.3639))
    date=request.args.get("date")

    tz=pytz.timezone(tzname)

    # AstroSage uses NOON anchor
    if date:
        y,m,d=map(int,date.split("-"))
        dt=tz.localize(datetime(y,m,d,12))
    else:
        dt=datetime.now(tz)

    return jsonify(panchang(dt,lat,lon,tzname))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
import os
import swisseph as swe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz

# Swiss Ephemeris data path
if os.path.exists("/usr/share/ephe"):
    swe.set_ephe_path("/usr/share/ephe")

app = Flask(__name__)
CORS(app)

# Lahiri Ayanamsa (AstroSage)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ================= TABLES =================

TITHI = [
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

KARANA = (
 ["Kimstughna"] +
 ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"] * 8 +
 ["Shakuni","Chatushpada","Naga"]
)

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya",
        "Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
        "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
        "Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
         "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi",
         "Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla",
         "Brahma","Indra","Vaidhriti"]

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
         "Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]

AMANTA = ["Chaitra","Vaisakha","Jyeshtha","Ashadha","Shravana","Bhadrapada",
          "Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]

RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

RAHU=[8,2,7,5,6,4,3]
YAMA=[5,4,3,2,1,7,6]
GULI=[7,6,5,4,3,2,1]

# ================= CORE =================

def jd(dt):
    return swe.julday(dt.year,dt.month,dt.day,
                      dt.hour+dt.minute/60+dt.second/3600)

def from_jd(j,tz):
    return datetime.fromtimestamp((j-2440587.5)*86400,tz)

def safe_calc(j,p):
    try:
        return swe.calc_ut(j,p,swe.FLG_SIDEREAL|swe.FLG_SWIEPH)[0][0]%360
    except:
        return swe.calc_ut(j,p)[0][0]%360

def sun_moon(j):
    return safe_calc(j,swe.SUN), safe_calc(j,swe.MOON)

def ang(a,b):
    return (a-b)%360

# ================= RISE / SET =================

def safe_rise(j,p,flag,geo):
    try:
        r=swe.rise_trans(j,p,flag,geo,atpress=0,attemp=0)
        if r and r[1] and len(r[1])>0:
            return r[1][0]
    except:
        pass
    return None

def sunrise(dt,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(dt.year,dt.month,dt.day,5))
    for h in [0,1,-1]:
        j=safe_rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_RISE,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunrise failed")

def sunset(dt,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(dt.year,dt.month,dt.day,12))
    for h in [0,1,-1]:
        j=safe_rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_SET,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunset failed")

def moon_event(dt,lat,lon,tz,flag):
    geo=(lon,lat,0)
    base=tz.localize(datetime(dt.year,dt.month,dt.day,6))
    for h in [0,1,-1]:
        j=safe_rise(jd(base+timedelta(hours=h)),swe.MOON,flag,geo)
        if j: return from_jd(j,tz)
    return None

# ================= ASTROSAGE EVENT SOLVER =================

def forward_solve(j0,target,fn):
    step=0.02
    j=j0
    prev=(fn(j)-target)%360
    for _ in range(2000):
        j+=step
        cur=(fn(j)-target)%360
        if prev>300 and cur<60:
            lo=j-step; hi=j
            break
        prev=cur
    for _ in range(40):
        mid=(lo+hi)/2
        if (fn(mid)-target)%360<180: hi=mid
        else: lo=mid
    return hi

# ================= ASTROSAGE DATE RESOLVER =================

def resolve_vedic_date(y,m,d,tz,lat,lon):
    civil = tz.localize(datetime(y,m,d,0,0))
    sr = sunrise(civil,lat,lon,tz)
    if civil < sr:
        civil -= timedelta(days=1)
    return civil

# ================= PANCHANG =================

def panchang(dt,lat,lon,tzname):
    tz=pytz.timezone(tzname)

    sr=sunrise(dt,lat,lon,tz)
    ss=sunset(dt,lat,lon,tz)

    j0=jd(sr)
    sun,moon=sun_moon(j0)

    diff=ang(moon,sun)
    t=int(diff/12)
    n=int(moon/13.3333333333)
    y=int(((sun+moon)%360)/13.3333333333)

    t_end=forward_solve(j0,(t+1)*12,lambda j:ang(sun_moon(j)[1],sun_moon(j)[0]))
    n_end=forward_solve(j0,(n+1)*13.3333333333,lambda j:safe_calc(j,swe.MOON))
    y_end=forward_solve(j0,(y+1)*13.3333333333,lambda j:(safe_calc(j,swe.SUN)+safe_calc(j,swe.MOON))%360)

    if t==0 and diff<6: kar="Kimstughna"
    else: kar=KARANA[int((diff-6)/6)%60]

    ama=forward_solve(j0,0,lambda j:ang(sun_moon(j)[1],sun_moon(j)[0]))
    sun_ama=safe_calc(ama,swe.SUN)
    amanta=AMANTA[int(sun_ama//30)%12]
    purni=AMANTA[(int(sun_ama//30)+1)%12]

    dur=ss-sr
    mins=dur.total_seconds()/60
    wd=(sr.weekday()+1)%7

    def seg(n): return (sr+timedelta(minutes=(n-1)*mins/8),sr+timedelta(minutes=n*mins/8))

    rahu=seg(RAHU[wd]); yama=seg(YAMA[wd]); guli=seg(GULI[wd])

    mr=moon_event(dt,lat,lon,tz,swe.CALC_RISE)
    ms=moon_event(dt,lat,lon,tz,swe.CALC_SET)

    return {
      "date":sr.strftime("%Y-%m-%d"),
      "day":sr.strftime("%A"),
      "tithi":TITHI[t],
      "tithi_end":from_jd(t_end,tz).strftime("%H:%M:%S"),
      "nakshatra":NAKS[n],
      "nakshatra_end":from_jd(n_end,tz).strftime("%H:%M:%S"),
      "yoga":YOGAS[y],
      "yoga_end":from_jd(y_end,tz).strftime("%H:%M:%S"),
      "karana":kar,
      "paksha":"Krishna" if t>=15 else "Shukla",
      "sunrise":sr.strftime("%H:%M:%S"),
      "sunset":ss.strftime("%H:%M:%S"),
      "moonrise":mr.strftime("%H:%M:%S") if mr else None,
      "moonset":ms.strftime("%H:%M:%S") if ms else None,
      "moon_sign":RASHI[int(moon//30)%12],
      "amanta_month":amanta,
      "purnimanta_month":purni,
      "ritu":RITU[int(sun//60)%6],
      "vikram_samvat":dt.year+57,
      "shaka_samvat":dt.year-78,
      "kali_samvat":dt.year+3101,
      "rahu_kalam":f"{rahu[0].strftime('%H:%M:%S')} - {rahu[1].strftime('%H:%M:%S')}",
      "yamaganda":f"{yama[0].strftime('%H:%M:%S')} - {yama[1].strftime('%H:%M:%S')}",
      "gulika":f"{guli[0].strftime('%H:%M:%S')} - {guli[1].strftime('%H:%M:%S')}",
      "abhijit":f"{(sr+dur*(7/15)).strftime('%H:%M:%S')} - {(sr+dur*(8/15)).strftime('%H:%M:%S')}"
    }

# ================= API =================

@app.route("/panchang")
def api():
    try:
        lat=float(request.args.get("lat",22.5726))
        lon=float(request.args.get("lon",88.3639))
        tzname=request.args.get("tz","Asia/Kolkata")
        tz=pytz.timezone(tzname)

        date=request.args.get("date")

        if date:
            y,m,d=map(int,date.split("-"))
            dt=resolve_vedic_date(y,m,d,tz,lat,lon)
        else:
            dt=datetime.now(tz)

        return jsonify(panchang(dt,lat,lon,tzname))
    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))

