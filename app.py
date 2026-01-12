import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz
import math

app = Flask(__name__)

# Lahiri ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

# --- CONSTANT TABLES ---

NAKS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha",
    "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula",
    "Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

TITHI = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami",
    "Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

KARANA = ["Bava","Balava","Kaulava","Taitila","Garija","Vanija","Vishti"] * 5

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
RITU = ["Vasanta","Grishma","Varsha","Sharad","Hemanta","Shishir"]

# Rahu, Yama, Gulika segment index by weekday (Mon=0 .. Sun=6)
RAHU_SEG   = [2,7,5,6,4,3,8]
YAMA_SEG   = [3,2,1,0,6,5,4]
GULIKA_SEG = [5,4,3,2,1,0,6]

DISHA = ["North-East","East","South-East","South","South-West","West","North-West"]

# Dushta Muhurta ghati ranges (Sun=0 .. Sat=6)
DUSHTA = {
    0:[(8,10),(14,16)],
    1:[(6,8),(12,14)],
    2:[(2,4),(10,12)],
    3:[(5,7),(11,13)],
    4:[(4,6),(13,15)],
    5:[(3,5),(9,11)],
    6:[(1,3),(8,10)]
}

HORA_SEQ = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]

CHOGH_DAY = [
 ["Amrit","Kaal","Shubh","Rog","Udveg","Chal","Labh","Amrit"],
 ["Rog","Udveg","Chal","Labh","Amrit","Kaal","Shubh","Rog"],
 ["Shubh","Rog","Udveg","Chal","Labh","Amrit","Kaal","Shubh"],
 ["Chal","Labh","Amrit","Kaal","Shubh","Rog","Udveg","Chal"],
 ["Labh","Amrit","Kaal","Shubh","Rog","Udveg","Chal","Labh"],
 ["Kaal","Shubh","Rog","Udveg","Chal","Labh","Amrit","Kaal"],
 ["Udveg","Chal","Labh","Amrit","Kaal","Shubh","Rog","Udveg"]
]

AMANTA = ["Chaitra","Vaisakha","Jyeshtha","Ashadha","Shravana","Bhadrapada",
          "Ashwin","Kartika","Margashirsha","Pausha","Magha","Phalguna"]

# --- HELPER FUNCTIONS ---

def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60 + dt.second/3600)

def jd_to_local(jd, tz):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400, tz)

def find_end(jd, fn, step=1/1440):
    v = fn(jd)
    j = jd
    for _ in range(2000):
        j += step
        if fn(j) != v:
            return j
    return j

def get_segment(sr, day_minutes, seg):
    start = sr + timedelta(minutes=seg * day_minutes / 8)
    end   = sr + timedelta(minutes=(seg + 1) * day_minutes / 8)
    return start, end

def ghati_range(sr, day_minutes, g1, g2):
    total_gh = 60
    s = sr + timedelta(minutes=(g1/total_gh)*day_minutes)
    e = sr + timedelta(minutes=(g2/total_gh)*day_minutes)
    return s, e

# --- API ---

@app.route("/panchang")
def panchang():
    try:
        lat = float(request.args.get("lat",22.57))
        lon = float(request.args.get("lon",88.36))
        tz  = request.args.get("tz","Asia/Kolkata")

        tzobj = pytz.timezone(tz)
        now = datetime.now(tzobj)
        jd = julian(now)
        geopos = (lon, lat, 0)

        sun = swe.calc_ut(jd, swe.SUN)[0][0]
        moon = swe.calc_ut(jd, swe.MOON)[0][0]

        diff = (moon - sun) % 360
        tithiIndex = min(29, int(diff / 12))
        nakIndex = int((moon % 360) / 13.333333)
        yogaIndex = int(((sun + moon) % 360) / 13.333333)

        tithiEnd = find_end(jd, lambda j: int(((swe.calc_ut(j,swe.MOON)[0][0] - swe.calc_ut(j,swe.SUN)[0][0]) % 360) / 12))
        nakEnd   = find_end(jd, lambda j: int((swe.calc_ut(j,swe.MOON)[0][0] % 360) / 13.333333))
        yogaEnd  = find_end(jd, lambda j: int(((swe.calc_ut(j,swe.SUN)[0][0] + swe.calc_ut(j,swe.MOON)[0][0]) % 360) / 13.333333))

        sunrise = swe.rise_trans(jd, swe.SUN, swe.CALC_RISE, geopos)[1][0]
        sunset  = swe.rise_trans(jd, swe.SUN, swe.CALC_SET,  geopos)[1][0]
        moonrise = swe.rise_trans(jd, swe.MOON, swe.CALC_RISE, geopos)[1][0]
        moonset  = swe.rise_trans(jd, swe.MOON, swe.CALC_SET,  geopos)[1][0]

        sr = jd_to_local(sunrise, tzobj)
        ss = jd_to_local(sunset, tzobj)
        daymins = (ss - sr).total_seconds() / 60

        wd = now.weekday()

        rahu_start, rahu_end = get_segment(sr, daymins, RAHU_SEG[wd])
        yama_start, yama_end = get_segment(sr, daymins, YAMA_SEG[wd])
        gulika_start, gulika_end = get_segment(sr, daymins, GULIKA_SEG[wd])

        mid = sr + timedelta(minutes=daymins/2)
        abh_start = mid - timedelta(minutes=24)
        abh_end   = mid + timedelta(minutes=24)

        dushta = []
        for g in DUSHTA[wd]:
            s,e = ghati_range(sr, daymins, g[0], g[1])
            dushta.append(f"{s.strftime('%H:%M:%S')} - {e.strftime('%H:%M:%S')}")

        moon_rashi = int((moon % 360) / 30)
        sun_rashi  = int((sun % 360) / 30)

        vara = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][wd]

        # Samvat
        greg = now.year
        vikram = greg + 57
        shaka = greg - 78
        kali = greg + 3101

        # Months
        amanta = AMANTA[sun_rashi]
        purnimanta = AMANTA[(sun_rashi + 1) % 12]

        # Hora
        day_lord = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"][wd]
        start = HORA_SEQ.index(day_lord)
        horas = [HORA_SEQ[(start+i)%7] for i in range(24)]
        hora_now = horas[int((now - sr).total_seconds()/3600)%24]

        # Choghadiya
        seg = int((now - sr).total_seconds() / (daymins*60/8))
        chogh = CHOGH_DAY[wd][seg]

        return jsonify({
            "tithi":TITHI[tithiIndex],
            "tithi_end":jd_to_local(tithiEnd, tzobj).strftime("%H:%M:%S"),
            "nakshatra":NAKS[nakIndex],
            "nakshatra_end":jd_to_local(nakEnd, tzobj).strftime("%H:%M:%S"),
            "karana":KARANA[(tithiIndex*2)%len(KARANA)],
            "paksha":"Shukla" if tithiIndex<15 else "Krishna",
            "yoga":yogaIndex+1,
            "yoga_end":jd_to_local(yogaEnd, tzobj).strftime("%H:%M:%S"),
            "vara":vara,
            "sunrise":sr.strftime("%H:%M:%S"),
            "sunset":ss.strftime("%H:%M:%S"),
            "moonrise":jd_to_local(moonrise, tzobj).strftime("%H:%M:%S"),
            "moonset":jd_to_local(moonset, tzobj).strftime("%H:%M:%S"),
            "rahu_kaal":f"{rahu_start.strftime('%H:%M:%S')} - {rahu_end.strftime('%H:%M:%S')}",
            "yamaganda":f"{yama_start.strftime('%H:%M:%S')} - {yama_end.strftime('%H:%M:%S')}",
            "gulika":f"{gulika_start.strftime('%H:%M:%S')} - {gulika_end.strftime('%H:%M:%S')}",
            "abhijit":f"{abh_start.strftime('%H:%M:%S')} - {abh_end.strftime('%H:%M:%S')}",
            "dushta_muhurta":dushta,
            "disha_shoola":DISHA[wd],
            "moon_rashi":RASHI[moon_rashi],
            "ritu":RITU[int((sun % 360) / 60)],
            "vikram_samvat":vikram,
            "shaka_samvat":shaka,
            "kali_samvat":kali,
            "amanta_month":amanta,
            "purnimanta_month":purnimanta,
            "hora":hora_now,
            "choghadiya":chogh
        })

    except Exception as e:
        return jsonify({"error":"Panchang Engine Error","details":str(e)}),500
