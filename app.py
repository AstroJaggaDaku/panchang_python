import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------- TABLES ----------

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

RAHU_SEG   = [2,7,5,6,4,3,8]
YAMA_SEG   = [3,2,1,0,6,5,4]
GULIKA_SEG = [5,4,3,2,1,0,6]

CHOGH = [
 ["Amrit","Kaal","Shubh","Rog","Udveg","Chal","Labh","Amrit"],
 ["Rog","Udveg","Chal","Labh","Amrit","Kaal","Shubh","Rog"],
 ["Shubh","Rog","Udveg","Chal","Labh","Amrit","Kaal","Shubh"],
 ["Chal","Labh","Amrit","Kaal","Shubh","Rog","Udveg","Chal"],
 ["Labh","Amrit","Kaal","Shubh","Rog","Udveg","Chal","Labh"],
 ["Kaal","Shubh","Rog","Udveg","Chal","Labh","Amrit","Kaal"],
 ["Udveg","Chal","Labh","Amrit","Kaal","Shubh","Rog","Udveg"]
]

# ---------- Helpers ----------

def safe(arr,i): return arr[int(i)%len(arr)]

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)

def jd_to_local(jd,tz):
    return datetime.fromtimestamp((jd-2440587.5)*86400,tz)

def find_end(jd,fn):
    base=fn(jd)
    j=jd
    for _ in range(1440):
        j+=1/1440
        if fn(j)!=base:
            return j
    return j

def muhurta(sr,daymins,seg):
    start=sr+timedelta(minutes=seg*daymins/8)
    end=sr+timedelta(minutes=(seg+1)*daymins/8)
    return start,end

# ---------- API ----------

@app.route("/panchang")
def panchang():
    try:
        lat=float(request.args.get("lat",22.57))
        lon=float(request.args.get("lon",88.36))
        tz=request.args.get("tz","Asia/Kolkata")
        tzobj=pytz.timezone(tz)

        # 🔥 FIX: Date support for Monthly / Festival
        date_str=request.args.get("date")
        if date_str:
            y,m,d=map(int,date_str.split("-"))
            now=tzobj.localize(datetime(y,m,d,12,0,0))   # noon prevents edge bugs
        else:
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

        sr=jd_to_local(sunrise,tzobj)
        ss=jd_to_local(sunset,tzobj)
        daymins=(ss-sr).total_seconds()/60
        wd=now.weekday()

        rahu_s,rahu_e=muhurta(sr,daymins,RAHU_SEG[wd])
        yama_s,yama_e=muhurta(sr,daymins,YAMA_SEG[wd])
        gulika_s,gulika_e=muhurta(sr,daymins,GULIKA_SEG[wd])

        mid=sr+timedelta(minutes=daymins/2)
        abh_s=mid-timedelta(minutes=24)
        abh_e=mid+timedelta(minutes=24)

        seg=int((now-sr).total_seconds()/(daymins*60/8))
        if seg<0: seg=0
        if seg>7: seg=7

        return jsonify({
            "date": now.strftime("%Y-%m-%d"),
            "tithi":safe(TITHI,tithiIndex),
            "tithi_end":jd_to_local(tithiEnd,tzobj).strftime("%H:%M:%S"),
            "nakshatra":safe(NAKS,nakIndex),
            "nakshatra_end":jd_to_local(nakEnd,tzobj).strftime("%H:%M:%S"),
            "karana":safe(KARANA,tithiIndex*2),
            "paksha":"Shukla" if tithiIndex<15 else "Krishna",
            "yoga":yogaIndex+1,
            "yoga_end":jd_to_local(yogaEnd,tzobj).strftime("%H:%M:%S"),
            "sunrise":sr.strftime("%H:%M:%S"),
            "sunset":ss.strftime("%H:%M:%S"),
            "rahu_kaal":f"{rahu_s.strftime('%H:%M:%S')} - {rahu_e.strftime('%H:%M:%S')}",
            "yamaganda":f"{yama_s.strftime('%H:%M:%S')} - {yama_e.strftime('%H:%M:%S')}",
            "gulika":f"{gulika_s.strftime('%H:%M:%S')} - {gulika_e.strftime('%H:%M:%S')}",
            "abhijit":f"{abh_s.strftime('%H:%M:%S')} - {abh_e.strftime('%H:%M:%S')}",
            "choghadiya":CHOGH[wd][seg],
            "moon_rashi":safe(RASHI,int(moon/30)),
            "ritu":safe(RITU,int(sun/60)),
            "amanta_month":safe(AMANTA,int(sun/30))
        })

    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500
