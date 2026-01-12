import swisseph as swe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ================== CONSTANTS ==================

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

RASHI = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
         "Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]

YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
         "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi",
         "Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla",
         "Brahma","Indra","Vaidhriti"]

# Drik Panchang Segments (SUNRISE based, Sun=0 .. Sat=6)
RAHU_SEG   = [8,2,7,5,6,4,3]
YAMA_SEG   = [5,4,3,2,1,7,6]
GULIKA_SEG = [7,6,5,4,3,2,1]

# ================== UTILITIES ==================

def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)

def jd_to_local(jd,tz):
    return datetime.fromtimestamp((jd-2440587.5)*86400,tz)

def muhurta(sr, daymins, seg):
    part = daymins / 8
    start = sr + timedelta(minutes=seg * part)
    end   = start + timedelta(minutes=part)
    return start, end

# ================== CORE ENGINE ==================

def drik_panchang(date, lat, lon, tz):
    tzobj = pytz.timezone(tz)

    # Always calculate from sunrise (Drik Panchang rule)
    base = tzobj.localize(datetime(date.year, date.month, date.day, 6, 0, 0))
    jd0 = julian(base)
    geopos = (lon, lat, 0)

    sunrise_jd = swe.rise_trans(jd0, swe.SUN, swe.CALC_RISE, geopos)[1][0]
    sunset_jd  = swe.rise_trans(jd0, swe.SUN, swe.CALC_SET, geopos)[1][0]

    sr = jd_to_local(sunrise_jd, tzobj)
    ss = jd_to_local(sunset_jd, tzobj)
    daymins = (ss - sr).total_seconds() / 60

    jd = julian(sr)

    sun = swe.calc_ut(jd, swe.SUN)[0][0] % 360
    moon = swe.calc_ut(jd, swe.MOON)[0][0] % 360

    diff = (moon - sun) % 360
    tithi_i = int(diff / 12)
    nak_i = int(moon / 13.333333)
    yoga_i = int(((sun + moon) % 360) / 13.333333)

    # 🌟 Correct Drik weekday (SUNRISE based)
    weekday = (sr.weekday() + 1) % 7   # Sunday=0

    rahu_s, rahu_e = muhurta(sr, daymins, RAHU_SEG[weekday]-1)
    yama_s, yama_e = muhurta(sr, daymins, YAMA_SEG[weekday]-1)
    guli_s, guli_e = muhurta(sr, daymins, GULIKA_SEG[weekday]-1)

    mid = sr + timedelta(minutes=daymins/2)
    abh_s = mid - timedelta(minutes=24)
    abh_e = mid + timedelta(minutes=24)

    return {
        "date": sr.strftime("%Y-%m-%d"),
        "day": sr.strftime("%A"),
        "tithi": TITHI[tithi_i],
        "nakshatra": NAKS[nak_i],
        "yoga": YOGAS[yoga_i],
        "paksha": "Krishna" if tithi_i >= 15 else "Shukla",
        "sunrise": sr.strftime("%H:%M:%S"),
        "sunset": ss.strftime("%H:%M:%S"),
        "moon_rashi": RASHI[int(moon/30)],
        "rahu_kaal": f"{rahu_s.strftime('%H:%M:%S')} - {rahu_e.strftime('%H:%M:%S')}",
        "yamaganda": f"{yama_s.strftime('%H:%M:%S')} - {yama_e.strftime('%H:%M:%S')}",
        "gulika": f"{guli_s.strftime('%H:%M:%S')} - {guli_e.strftime('%H:%M:%S')}",
        "abhijit": f"{abh_s.strftime('%H:%M:%S')} - {abh_e.strftime('%H:%M:%S')}"
    }

# ================== API ==================

@app.route("/panchang")
def api():
    lat = float(request.args.get("lat",22.57))
    lon = float(request.args.get("lon",88.36))
    tz  = request.args.get("tz","Asia/Kolkata")
    date = request.args.get("date")

    if date:
        y,m,d = map(int,date.split("-"))
        dt = datetime(y,m,d)
    else:
        dt = datetime.now(pytz.timezone(tz))

    return jsonify(drik_panchang(dt,lat,lon,tz))
