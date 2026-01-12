import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ================= TABLES =================

TITHI = [
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
 "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
 "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

# 60 Karana system (AstroSage standard)
KARANA = (["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"] * 8) + \
         ["Shakuni","Chatushpada","Naga","Kimstughna"]

NAKS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya",
        "Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
        "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
        "Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
         "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi",
         "Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla",
         "Brahma","Indra","Vaidhriti"]

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
AMANTA = ["Chaitra","Vaisakha","Jyeshtha","Ashadha","Shravana","Bhadrapada","Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]
RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

RAHU=[8,2,7,5,6,4,3]
YAMA=[5,4,3,2,1,7,6]
GULI=[7,6,5,4,3,2,1]

# ================= SAFE WRAPPERS =================

def safe_calc(jd, planet):
    try:
        return swe.calc_ut(jd, planet)[0][0] % 360
    except:
        return None

def safe_rise(jd, planet, flag, geo):
    try:
        r = swe.rise_trans(jd, planet, flag, geo)
        if r and r[1] and len(r[1]) > 0:
            return r[1][0]
    except:
        pass
    return None

# ================= TIME =================

def jd(dt):
    return swe.julday(dt.year,dt.month,dt.day,
                      dt.hour+dt.minute/60+dt.second/3600)

def from_jd(jd,tz):
    return datetime.fromtimestamp((jd-2440587.5)*86400,tz)

# ================= TRUE RISE / SET =================

FLAG = swe.BIT_DISC_CENTER | swe.BIT_TOPOCTR

def sunrise(date,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(date.year,date.month,date.day,5))
    for h in [0,1,-1]:
        j = safe_rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_RISE|FLAG,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunrise failed")

def sunset(date,lat,lon,tz):
    geo=(lon,lat,0)
    base=tz.localize(datetime(date.year,date.month,date.day,12))
    for h in [0,1,-1]:
        j = safe_rise(jd(base+timedelta(hours=h)),swe.SUN,swe.CALC_SET|FLAG,geo)
        if j: return from_jd(j,tz)
    raise Exception("Sunset failed")

def moon_event(date,lat,lon,tz,flag):
    geo=(lon,lat,0)
    base=tz.localize(datetime(date.year,date.month,date.day,6))
    for h in [0,1,-1]:
        j = safe_rise(jd(base+timedelta(hours=h)),swe.MOON,flag|FLAG,geo)
        if j: return from_jd(j,tz)
    return None

# ================= SOLVERS =================

def ang(a,b): return (a-b)%360

def sun_moon(j):
    return safe_calc(j,swe.SUN), safe_calc(j,swe.MOON)

def solve(start,target,fn):
    lo=start; hi=start+1
    for _ in range(50):
        mid=(lo+hi)/2
        if (fn(mid)-target+360)%360 < 180:
            hi=mid
        else:
            lo=mid
    return hi

# ================= PANCHANG =================

def panchang(date,lat,lon,tzname):
    tz=pytz.timezone(tzname)

    sr=sunrise(date,lat,lon,tz)
    ss=sunset(date,lat,lon,tz)

    j0=jd(sr)
    sun,moon=sun_moon(j0)
    diff=ang(moon,sun)

    t=int(diff/12)
    n=int(moon/13.3333333333)
    y=int(((sun+moon)%360)/13.3333333333)

    t_end=solve(j0,(t+1)*12,lambda j: ang(sun_moon(j)[1],sun_moon(j)[0]))
    n_end=solve(j0,(n+1)*13.3333333333,lambda j: sun_moon(j)[1]%360)
    y_end=solve(j0,(y+1)*13.3333333333,lambda j: (sun_moon(j)[0]+sun_moon(j)[1])%360)

    kar=KARANA[int(diff/6)%60]

    ama=solve(j0,0,lambda j: ang(sun_moon(j)[1],sun_moon(j)[0]))
    sun_ama=sun_moon(ama)[0]
    amanta=AMANTA[int(sun_ama/30)]
    purni=AMANTA[(int(sun_ama/30)+1)%12]

    vikram=date.year+57
    shaka=date.year-78
    kali=date.year+3101

    dur=ss-sr
    abh=(sr+dur*(7/15),sr+dur*(8/15))

    mins=dur.total_seconds()/60
    wd=(sr.weekday()+1)%7
    def seg(n):
        return (sr+timedelta(minutes=(n-1)*mins/8),
                sr+timedelta(minutes=n*mins/8))

    rahu=seg(RAHU[wd]); yama=seg(YAMA[wd]); guli=seg(GULI[wd])

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
      "moonrise":moon_event(date,lat,lon,tz,swe.CALC_RISE).strftime("%H:%M:%S"),
      "moonset":moon_event(date,lat,lon,tz,swe.CALC_SET).strftime("%H:%M:%S"),
      "moon_sign":RASHI[int(moon/30)],
      "amanta_month":amanta,
      "purnimanta_month":purni,
      "ritu":RITU[int(sun/60)],
      "vikram_samvat":vikram,
      "shaka_samvat":shaka,
      "kali_samvat":kali,
      "rahu_kalam":f"{rahu[0].strftime('%H:%M:%S')} - {rahu[1].strftime('%H:%M:%S')}",
      "yamaganda":f"{yama[0].strftime('%H:%M:%S')} - {yama[1].strftime('%H:%M:%S')}",
      "gulika":f"{guli[0].strftime('%H:%M:%S')} - {guli[1].strftime('%H:%M:%S')}",
      "abhijit":f"{abh[0].strftime('%H:%M:%S')} - {abh[1].strftime('%H:%M:%S')}"
    }

# ================= API =================

@app.route("/panchang")
def api():
    try:
        lat=float(request.args.get("lat",22.5726))
        lon=float(request.args.get("lon",88.3639))
        tz=request.args.get("tz","Asia/Kolkata")
        date=request.args.get("date")

        if date:
            y,m,d=map(int,date.split("-"))
            dt=datetime(y,m,d)
        else:
            dt=datetime.now(pytz.timezone(tz))

        return jsonify(panchang(dt,lat,lon,tz))
    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500

if __name__=="__main__":
    app.run()
