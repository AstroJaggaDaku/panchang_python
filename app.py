import os
import swisseph as swe
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pytz

# =========================================================
# Swiss Ephemeris
# =========================================================
if os.path.exists("/usr/share/ephe"):
    swe.set_ephe_path("/usr/share/ephe")

swe.set_sid_mode(swe.SIDM_LAHIRI)

app = Flask(__name__)
CORS(app)

# =========================================================
# CONSTANT TABLES
# =========================================================

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

# Rahu Yama Gulika (Sunday=0)
RAHU = [8,2,7,5,6,4,3]
YAMA = [5,4,3,2,1,7,6]
GULI = [7,6,5,4,3,2,1]

# Hora lords
WEEKDAY_LORD = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
HORA_SEQ = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]

# Varjyam degree table (sample classical)
VARJYAM = {
 "Ashwini":[(3,6)], "Bharani":[(6,9)], "Krittika":[(2,5)], "Rohini":[(7,10)],
 "Mrigashirsha":[(1,4)], "Ardra":[(9,12)], "Punarvasu":[(4,7)], "Pushya":[(6,9)],
 "Ashlesha":[(3,6)], "Magha":[(5,8)], "Purva Phalguni":[(1,4)], "Uttara Phalguni":[(7,10)],
 "Hasta":[(2,5)], "Chitra":[(6,9)], "Swati":[(3,6)], "Vishakha":[(5,8)],
 "Anuradha":[(1,4)], "Jyeshtha":[(7,10)], "Mula":[(2,5)], "Purva Ashadha":[(6,9)],
 "Uttara Ashadha":[(3,6)], "Shravana":[(5,8)], "Dhanishta":[(1,4)], "Shatabhisha":[(7,10)],
 "Purva Bhadrapada":[(2,5)], "Uttara Bhadrapada":[(6,9)], "Revati":[(3,6)]
}

# Festivals (Amanta)
FESTIVALS = {
 ("Amavasya","Ashwin"):"Diwali",
 ("Pratipada","Ashwin"):"Govardhan Puja",
 ("Navami","Ashwin"):"Durga Navami",
 ("Dashami","Ashwin"):"Vijaya Dashami",
 ("Purnima","Phalguna"):"Holi"
}

# =========================================================
# CORE
# =========================================================

def jd(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60)

def from_jd(j,tz):
    return datetime.fromtimestamp((j-2440587.5)*86400,tz)

def calc(j,p):
    return swe.calc_ut(j,p,swe.FLG_SIDEREAL|swe.FLG_SWIEPH)[0][0]%360

def ang(a,b): return (a-b)%360

# =========================================================
# RISE / SET
# =========================================================

def rise_set(j,p,flag,geo):
    r=swe.rise_trans(j,p,flag,geo,atpress=0,attemp=0)
    return r[1][0] if r and r[1] else None

def sunrise(date,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(date.year,date.month,date.day,6))
    for h in [0,1,-1]:
        j=rise_set(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_RISE,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunrise failed")

def sunset(sr,lat,lon,tz):
    geo=(lon,lat,0)
    base=sr+timedelta(hours=6)
    for h in [0,1,-1]:
        j=rise_set(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_SET,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunset failed")

def moon_event(date,lat,lon,tz,flag):
    geo=(lon,lat,0)
    base=tz.localize(datetime(date.year,date.month,date.day,6))
    for h in [0,1,-1]:
        j=rise_set(jd(base+timedelta(hours=h)),swe.MOON,flag,geo)
        if j: return from_jd(j,tz)
    return None

# =========================================================
# EVENT SOLVER
# =========================================================

def forward_solve(j0,target,fn):
    step=0.02
    j=j0
    prev=(fn(j)-target)%360
    for _ in range(2000):
        j+=step
        cur=(fn(j)-target)%360
        if prev>270 and cur<90:
            lo=j-step; hi=j; break
        prev=cur
    for _ in range(40):
        mid=(lo+hi)/2
        if (fn(mid)-target)%360<180: hi=mid
        else: lo=mid
    return hi

# =========================================================
# PANCHANG
# =========================================================

def panchang(date,lat,lon,tzname):
    tz=pytz.timezone(tzname)
    sr=sunrise(date,lat,lon,tz)
    ss=sunset(sr,lat,lon,tz)
    j0=jd(sr)

    sun=calc(j0,swe.SUN)
    moon=calc(j0,swe.MOON)
    diff=ang(moon,sun)

    t=int(diff/12)
    n=int(moon/13.3333333333)
    y=int(((sun+moon)%360)/13.3333333333)

    t_end=forward_solve(j0,(t+1)*12,lambda j:ang(calc(j,swe.MOON),calc(j,swe.SUN)))
    n_end=forward_solve(j0,(n+1)*13.3333333333,lambda j:calc(j,swe.MOON))
    y_end=forward_solve(j0,(y+1)*13.3333333333,lambda j:(calc(j,swe.SUN)+calc(j,swe.MOON))%360)

    kar=KARANA[int(diff/6)%60] if not(t==0 and diff<6) else "Kimstughna"

    ama=forward_solve(j0,0,lambda j:ang(calc(j,swe.MOON),calc(j,swe.SUN)))
    amanta=AMANTA[int(calc(ama,swe.SUN)//30)%12]
    purni=AMANTA[(int(calc(ama,swe.SUN)//30)+1)%12]

    # Abhijit latitude corrected
    mid=sr+(ss-sr)/2
    corr=timedelta(minutes=(lat/90)*6)
    abh=(mid-corr,mid+corr)

    # Varjyam
    deg_in_nak=moon%13.3333333333
    varj="No"
    if NAKS[n] in VARJYAM:
        for a,b in VARJYAM[NAKS[n]]:
            if a<=deg_in_nak<=b: varj="Yes"

    # Hora
    start_lord=WEEKDAY_LORD[sr.weekday()]
    idx=HORA_SEQ.index(start_lord)
    hora=[]
    cur=sr
    span=(ss-sr)/12
    for i in range(12):
        hora.append({"lord":HORA_SEQ[(idx+i)%7],
                     "from":(cur+span*i).strftime("%H:%M"),
                     "to":(cur+span*(i+1)).strftime("%H:%M")})

    # Festival
    fest=FESTIVALS.get((TITHI[t],amanta),"None")

    mr=moon_event(date,lat,lon,tz,swe.CALC_RISE)
    ms=moon_event(date,lat,lon,tz,swe.CALC_SET)

    return {
      "date":sr.strftime("%Y-%m-%d"),
      "day":sr.strftime("%A"),
      "sunrise":sr.strftime("%H:%M:%S"),
      "sunset":ss.strftime("%H:%M:%S"),
      "moonrise":mr.strftime("%H:%M:%S") if mr else None,
      "moonset":ms.strftime("%H:%M:%S") if ms else None,
      "tithi":TITHI[t],
      "tithi_end":from_jd(t_end,tz).strftime("%H:%M:%S"),
      "nakshatra":NAKS[n],
      "nakshatra_end":from_jd(n_end,tz).strftime("%H:%M:%S"),
      "yoga":YOGAS[y],
      "yoga_end":from_jd(y_end,tz).strftime("%H:%M:%S"),
      "karana":kar,
      "paksha":"Krishna" if t>=15 else "Shukla",
      "moon_sign":RASHI[int(moon//30)%12],
      "amanta_month":amanta,
      "purnimanta_month":purni,
      "ritu":RITU[int(sun//60)%6],
      "abhijit":f"{abh[0].strftime('%H:%M:%S')} - {abh[1].strftime('%H:%M:%S')}",
      "hora":hora,
      "varjyam":varj,
      "festival":fest
    }

# =========================================================
# API
# =========================================================

@app.route("/panchang")
def api():
    lat=float(request.args.get("lat",22.5726))
    lon=float(request.args.get("lon",88.3639))
    tz=request.args.get("tz","Asia/Kolkata")
    date=request.args.get("date")

    if date:
        y,m,d=map(int,date.split("-"))
        dt=pytz.timezone(tz).localize(datetime(y,m,d,12))
    else:
        dt=datetime.now(pytz.timezone(tz))

    return jsonify(panchang(dt,lat,lon,tz))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
