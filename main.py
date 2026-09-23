import logging
import os
import sys
import asyncio
import base64
import re
import httpx
import hashlib
import json
import html
from io import StringIO, BytesIO
from datetime import datetime, timedelta, timezone
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler
)

# =========================================================================
# --- WINDOWS TERMINAL UNICODE FIX & ADVANCED LOGGING ---
# =========================================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_core_debug.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

# =========================================================================
# --- PREMIUM EMOJI & FULL RAW FLAG DATABASES ---
# =========================================================================
PEM = {
    "ok": '<tg-emoji emoji-id="5352694861990501856"></tg-emoji>',
    "no": '<tg-emoji emoji-id="5420130255174145507"></tg-emoji>',
    "warn": '<tg-emoji emoji-id="5336944168944047463"></tg-emoji>',
    "admin": '<tg-emoji emoji-id="5353032893096567467"></tg-emoji>',
    "user": '<tg-emoji emoji-id="5352861489541714456"></tg-emoji>',
    "file": '<tg-emoji emoji-id="5352721946054268944"></tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5352597830089347330"></tg-emoji>',
    "graph": '<tg-emoji emoji-id="5352877703043258544"></tg-emoji>',
    "money": '<tg-emoji emoji-id="5348469219761626211"></tg-emoji>',
    "gift": '<tg-emoji emoji-id="5420396762189831222"></tg-emoji>',
    "msg": '<tg-emoji emoji-id="5337302974806922068"></tg-emoji>',
    "gear": '<tg-emoji emoji-id="5420155432272438703"></tg-emoji>',
    "link": '<tg-emoji emoji-id="5420517437885943844"></tg-emoji>',
    "trash": '<tg-emoji emoji-id="5422557736330106570"></tg-emoji>',
    "upload": '<tg-emoji emoji-id="5353001161878182134"></tg-emoji>',
    "world": '<tg-emoji emoji-id="5336972142066047577"></tg-emoji>',
    "lock": '<tg-emoji emoji-id="5353022963132174959"></tg-emoji>',
    "phone": '<tg-emoji emoji-id="5337132498965010628"></tg-emoji>',
    "num": '<tg-emoji emoji-id="5352862640592949843"></tg-emoji>',
    "pin": '<tg-emoji emoji-id="5352922460897452503"></tg-emoji>',
    "star": '<tg-emoji emoji-id="5352552689983067014"></tg-emoji>',
    "hi": '<tg-emoji emoji-id="5353027129250453493"></tg-emoji>',
    "bkash": '<tg-emoji emoji-id="6334668932980415143"></tg-emoji>',
    "nagad": '<tg-emoji emoji-id="6334715949987404568"></tg-emoji>',
    "binance": '<tg-emoji emoji-id="6334330042880893669"></tg-emoji>',
    "new_em": '<tg-emoji emoji-id="5382357040008021292">🆕</tg-emoji>',
    "top_em": '<tg-emoji emoji-id="5415655814079723871">🔝</tg-emoji>',
    "msg_em": '<tg-emoji emoji-id="6064179391691235813">✉️</tg-emoji>',
    "srv_em": '<tg-emoji emoji-id="6325653186740756740">👉</tg-emoji>',
    "lb_head": '<tg-emoji emoji-id="6328103684626456498">📈</tg-emoji>',
    "lb_1": '<tg-emoji emoji-id="5305763715692377402">1️⃣</tg-emoji>',
    "lb_2": '<tg-emoji emoji-id="5307907239380528763">2️⃣</tg-emoji>',
    "lb_3": '<tg-emoji emoji-id="5305783000095537258">3️⃣</tg-emoji>',
    "lb_4": '<tg-emoji emoji-id="5305255243104138538">4️⃣</tg-emoji>',
    "lb_5": '<tg-emoji emoji-id="5305288155438526869">5️⃣</tg-emoji>',
    "lb_6": '<tg-emoji emoji-id="5305642863902604489">6️⃣</tg-emoji>',
    "lb_7": '<tg-emoji emoji-id="5305603955793867793">7️⃣</tg-emoji>',
    "lb_8": '<tg-emoji emoji-id="5305371288825509083">8️⃣</tg-emoji>',
    "lb_9": '<tg-emoji emoji-id="5307703499016910744">9️⃣</tg-emoji>',
    "lb_10": '<tg-emoji emoji-id="5325605983563558400">😀</tg-emoji>'
}

RAW_FLAG_EMOJIS = {
    "US": {"phone_code": "1", "name": "United States", "id": "5913463998522592692"},
    "UA": {"phone_code": "380", "name": "Ukraine", "id": "5911406692007941050"},
    "PL": {"phone_code": "48", "name": "Poland", "id": "5913550391789752571"},
    "KZ": {"phone_code": "7", "name": "Kazakhstan", "id": "5913724621433082323"},
    "CN": {"phone_code": "86", "name": "China", "id": "5913779335021466780"},
    "AZ": {"phone_code": "994", "name": "Azerbaijan", "id": "5911197578640233518"},
    "EU": {"phone_code": "?", "name": "European Union", "id": "5911106310585193018"},
    "AM": {"phone_code": "374", "name": "Armenia", "id": "5913272455866093666"},
    "RU": {"phone_code": "79", "name": "Russia", "id": "5913274246867456342"},
    "UZ": {"phone_code": "998", "name": "Uzbekistan", "id": "5911051846104912282"},
    "DE": {"phone_code": "49", "name": "Germany", "id": "5911096835887337583"},
    "JP": {"phone_code": "81", "name": "Japan", "id": "5913293711659241040"},
    "TR": {"phone_code": "90", "name": "Turkey", "id": "5910995113881901195"},
    "BY": {"phone_code": "375", "name": "Belarus", "id": "5911011185649521599"},
    "GB": {"phone_code": "44", "name": "United Kingdom", "id": "5913443365499703513"},
    "IN": {"phone_code": "91", "name": "India", "id": "5913754823643107921"},
    "BR": {"phone_code": "55", "name": "Brazil", "id": "5911148568768418614"},
    "ZM": {"phone_code": "260", "name": "Zambia", "id": "5913564754160389778"},
    "YE": {"phone_code": "967", "name": "Yemen", "id": "5913346492512341993"},
    "WALES": {"phone_code": "44", "name": "Wales", "id": "5911297801702084799"},
    "VN": {"phone_code": "84", "name": "Vietnam", "id": "5913428887164949581"},
    "VA": {"phone_code": "379", "name": "Holy See (Vatican City State)", "id": "5911211932420938860"},
    "VU": {"phone_code": "678", "name": "Vanuatu", "id": "5913511535220625585"},
    "UY": {"phone_code": "598", "name": "Uruguay", "id": "5913623088406204470"},
    "AE": {"phone_code": "971", "name": "United Arab Emirates", "id": "5913726554168365343"},
    "UG": {"phone_code": "256", "name": "Uganda", "id": "5913488939397681980"},
    "TM": {"phone_code": "993", "name": "Turkmenistan", "id": "5913315521503170180"},
    "TN": {"phone_code": "216", "name": "Tunisia", "id": "5911332947419468671"},
    "TT": {"phone_code": "1", "name": "Trinidad and Tobago", "id": "5911228635548750294"},
    "TG": {"phone_code": "228", "name": "Togo", "id": "5913423260757790970"},
    "TH": {"phone_code": "66", "name": "Thailand", "id": "5913617968805187987"},
    "TZ": {"phone_code": "255", "name": "Tanzania", "id": "5911418949844603556"},
    "TJ": {"phone_code": "992", "name": "Tajikistan", "id": "5911287639809463107"},
    "CH": {"phone_code": "41", "name": "Switzerland", "id": "5913271227505448072"},
    "SE": {"phone_code": "46", "name": "Sweden", "id": "5911156510162949403"},
    "SZ": {"phone_code": "268", "name": "Eswatini (Swaziland)", "id": "5913374525763883286"},
    "SR": {"phone_code": "597", "name": "Suriname", "id": "5913275539652611719"},
    "SD": {"phone_code": "249", "name": "Sudan", "id": "5911387497799094470"},
    "ES": {"phone_code": "34", "name": "Spain", "id": "5911193287967904547"},
    "LK": {"phone_code": "94", "name": "Sri Lanka", "id": "5911293163137406640"},
    "SS": {"phone_code": "211", "name": "South Sudan", "id": "5911406262511211744"},
    "ZA": {"phone_code": "27", "name": "South Africa", "id": "5911203119148044594"},
    "SO": {"phone_code": "252", "name": "Somalia", "id": "5911397852965244436"},
    "SB": {"phone_code": "677", "name": "Solomon Islands", "id": "5911482712929080608"},
    "SI": {"phone_code": "386", "name": "Slovenia", "id": "5913431983836368644"},
    "SK": {"phone_code": "421", "name": "Slovakia", "id": "5913751666842145020"},
    "SG": {"phone_code": "65", "name": "Singapore", "id": "5911531460808051849"},
    "SL": {"phone_code": "232", "name": "Sierra Leone", "id": "5911210450657218661"},
    "SC": {"phone_code": "248", "name": "Seychelles", "id": "5911185183364616913"},
    "RS": {"phone_code": "381", "name": "Serbia", "id": "5913592598433369871"},
    "SN": {"phone_code": "221", "name": "Senegal", "id": "5910995302860461643"},
    "SCOTLAND": {"phone_code": "44", "name": "Scotland", "id": "5911460091336331851"},
    "ST": {"phone_code": "239", "name": "Sao Tome and Principe", "id": "5913574331937462345"},
    "SM": {"phone_code": "378", "name": "San Marino", "id": "5913587968458625465"},
    "WS": {"phone_code": "685", "name": "Samoa", "id": "5913325971158602854"},
    "KN": {"phone_code": "1", "name": "Saint Kitts and Nevis", "id": "5913691898077253637"},
    "VC": {"phone_code": "1", "name": "Saint Vincent and the Grenadines", "id": "5911318941531116255"},
    "LC": {"phone_code": "1", "name": "Saint Lucia", "id": "5911243659344351824"},
    "PS": {"phone_code": "970", "name": "Palestine", "id": "5913684768431541668"},
    "RW": {"phone_code": "250", "name": "Rwanda", "id": "5911455229433352234"},
    "RO": {"phone_code": "40", "name": "Romania", "id": "5913460373570195273"},
    "QA": {"phone_code": "974", "name": "Qatar", "id": "5911260864983339619"},
    "PR": {"phone_code": "1", "name": "Puerto Rico", "id": "5911504350974317480"},
    "PT": {"phone_code": "351", "name": "Portugal", "id": "5911023653939581472"},
    "PH": {"phone_code": "63", "name": "Philippines", "id": "5911268638874145162"},
    "PE": {"phone_code": "51", "name": "Peru", "id": "5911207993935925780"},
    "PY": {"phone_code": "595", "name": "Paraguay", "id": "5911014265141072316"},
    "PG": {"phone_code": "675", "name": "Papua", "id": "5911107251183030903"},
    "PA": {"phone_code": "507", "name": "Panama", "id": "5913428968769327174"},
    "PW": {"phone_code": "680", "name": "Palau", "id": "5911283903187915549"},
    "PK": {"phone_code": "92", "name": "Pakistan", "id": "5913705895375672082"},
    "OM": {"phone_code": "968", "name": "Oman", "id": "5913570801474343473"},
    "NO": {"phone_code": "47", "name": "Norway", "id": "5913617397574537046"},
    "NG": {"phone_code": "234", "name": "Nigeria", "id": "5911143844304393105"},
    "NE": {"phone_code": "227", "name": "Niger", "id": "5911270086278124251"},
    "NZ": {"phone_code": "64", "name": "New Zealand", "id": "5913640044937089340"},
    "NL": {"phone_code": "31", "name": "Netherlands", "id": "5913367645226275100"},
    "NP": {"phone_code": "977", "name": "Nepal", "id": "5913496520014958723"},
    "NA": {"phone_code": "264", "name": "Namibia", "id": "5911108535378252443"},
    "MZ": {"phone_code": "258", "name": "Mozambique", "id": "5911333419865871464"},
    "MA": {"phone_code": "212", "name": "Morocco", "id": "5911482111633658301"},
    "ME": {"phone_code": "382", "name": "Montenegro", "id": "5913239436157522151"},
    "MN": {"phone_code": "976", "name": "Mongolia", "id": "5911041383564580038"},
    "MC": {"phone_code": "377", "name": "Monaco", "id": "5911245347266500057"},
    "MD": {"phone_code": "373", "name": "Moldova, Republic of", "id": "5913456847402045950"},
    "MV": {"phone_code": "960", "name": "Maldives", "id": "5913501399097806832"},
    "ML": {"phone_code": "223", "name": "Mali", "id": "5911305266355245916"},
    "MT": {"phone_code": "356", "name": "Malta", "id": "5911023714069123567"},
    "BM": {"phone_code": "1", "name": "Bermuda", "id": "5913680005312811090"},
    "MQ": {"phone_code": "596", "name": "Martinique", "id": "5911378005921370347"},
    "MH": {"phone_code": "692", "name": "Marshall Islands", "id": "5913235935759175692"},
    "MU": {"phone_code": "230", "name": "Mauritius", "id": "5913291113204027321"},
    "MX": {"phone_code": "52", "name": "Mexico", "id": "5913687302462246518"},
    "FM": {"phone_code": "691", "name": "Micronesia, Federated States of", "id": "5911271104185373336"},
    "MY": {"phone_code": "60", "name": "Malaysia", "id": "5913654360063087453"},
    "KE": {"phone_code": "254", "name": "Kenya", "id": "5911154710571651231"},
    "MG": {"phone_code": "261", "name": "Madagascar", "id": "5913766918271012920"},
    "MK": {"phone_code": "389", "name": "Republic of North Macedonia", "id": "5913394029210374721"},
    "LU": {"phone_code": "352", "name": "Luxembourg", "id": "5913390842344640293"},
    "LT": {"phone_code": "370", "name": "Lithuania", "id": "5911172315642597775"},
    "LI": {"phone_code": "423", "name": "Liechtenstein", "id": "5911166650580734660"},
    "LY": {"phone_code": "218", "name": "Libya", "id": "5911236989260140996"},
    "LR": {"phone_code": "231", "name": "Liberia", "id": "5913324167272337727"},
    "KI": {"phone_code": "686", "name": "Kiribati", "id": "5911294443037660118"},
    "XK": {"phone_code": "383", "name": "Kosovo", "id": "5911433681582429010"},
    "KW": {"phone_code": "965", "name": "Kuwait", "id": "5913290705182134003"},
    "KG": {"phone_code": "996", "name": "Kyrgyzstan", "id": "5911202161370337549"},
    "LA": {"phone_code": "856", "name": "Laos", "id": "5913718526874489279"},
    "LV": {"phone_code": "371", "name": "Latvia", "id": "5913738489882480243"},
    "LB": {"phone_code": "961", "name": "Lebanon", "id": "5911504273664905447"},
    "LS": {"phone_code": "266", "name": "Lesotho", "id": "5911059881988723711"},
    "ID": {"phone_code": "62", "name": "Indonesia", "id": "5913479361620611038"},
    "IR": {"phone_code": "98", "name": "Iran", "id": "5911308891307643032"},
    "IQ": {"phone_code": "964", "name": "Iraq", "id": "5911382442622587735"},
    "IE": {"phone_code": "353", "name": "Ireland", "id": "5913440715504881532"},
    "IL": {"phone_code": "972", "name": "Israel", "id": "5911471936856134692"},
    "IT": {"phone_code": "39", "name": "Italy", "id": "5913688444923547525"},
    "JM": {"phone_code": "1", "name": "Jamaica", "id": "5913232280742006526"},
    "JO": {"phone_code": "962", "name": "Jordan", "id": "5913234136167878475"},
    "IS": {"phone_code": "354", "name": "Iceland", "id": "5911047899029967246"},
    "HU": {"phone_code": "36", "name": "Hungary", "id": "5913767635530551104"},
    "HN": {"phone_code": "504", "name": "Honduras", "id": "5911406889576436289"},
    "HT": {"phone_code": "509", "name": "Haiti", "id": "5913459789454643194"},
    "GY": {"phone_code": "592", "name": "Guyana", "id": "5913579412883771480"},
    "GW": {"phone_code": "245", "name": "Bissau", "id": "5911398694778836149"},
    "GN": {"phone_code": "224", "name": "Guinea", "id": "5913471858312744319"},
    "GT": {"phone_code": "502", "name": "Guatemala", "id": "5913324858762072330"},
    "GD": {"phone_code": "1", "name": "Grenada", "id": "5913228063084121946"},
    "GR": {"phone_code": "30", "name": "Greece", "id": "5911210399117611448"},
    "GH": {"phone_code": "233", "name": "Ghana", "id": "5913391155877252952"},
    "GE": {"phone_code": "995", "name": "Georgia", "id": "5913434771270144023"},
    "GM": {"phone_code": "220", "name": "Gambia", "id": "5913657267755945883"},
    "GA": {"phone_code": "241", "name": "Gabon", "id": "5911037896051137264"},
    "FR": {"phone_code": "33", "name": "France", "id": "5913605586414473124"},
    "FI": {"phone_code": "358", "name": "Finland", "id": "5911041344909873378"},
    "FJ": {"phone_code": "679", "name": "Fiji", "id": "5911393832875856716"},
    "ET": {"phone_code": "251", "name": "Ethiopia", "id": "5911078333168227043"},
    "DO": {"phone_code": "1", "name": "Dominican Republic", "id": "5911152099231536123"},
    "TL": {"phone_code": "670", "name": "Timor-Leste", "id": "5911141915864076479"},
    "EC": {"phone_code": "593", "name": "Ecuador", "id": "5911273865849347408"},
    "EG": {"phone_code": "20", "name": "Egypt", "id": "5913694831539916769"},
    "SV": {"phone_code": "503", "name": "El Salvador", "id": "5913238624408703010"},
    "ENGLAND": {"phone_code": "44", "name": "England", "id": "5913475719488344315"},
    "EE": {"phone_code": "372", "name": "Estonia", "id": "5910986042910969906"},
    "DM": {"phone_code": "1", "name": "Dominica", "id": "5911377121158107430"},
    "DJ": {"phone_code": "253", "name": "Djibouti", "id": "5911407709915190157"},
    "DK": {"phone_code": "45", "name": "Denmark", "id": "5911206009661034712"},
    "CY": {"phone_code": "357", "name": "Cyprus", "id": "5911023550860366409"},
    "HR": {"phone_code": "385", "name": "Croatia", "id": "5913692684056269311"},
    "CR": {"phone_code": "506", "name": "Costa Rica", "id": "5911261745451635030"},
    "CG": {"phone_code": "242", "name": "Congo", "id": "5911338788574990168"},
    "CD": {"phone_code": "243", "name": "Congo, The Democratic Republic of the", "id": "5913770362834783827"},
    "KM": {"phone_code": "269", "name": "Comoros", "id": "5911338582416560604"},
    "KH": {"phone_code": "855", "name": "Cambodia", "id": "5913699998385573485"},
    "CM": {"phone_code": "237", "name": "Cameroon", "id": "5911172109484167745"},
    "CA": {"phone_code": "1", "name": "Canada", "id": "5913623736946265914"},
    "CV": {"phone_code": "238", "name": "Cape Verde", "id": "5913571501554012193"},
    "CF": {"phone_code": "236", "name": "Central African Republic", "id": "5913443245240619222"},
    "TD": {"phone_code": "235", "name": "Chad", "id": "5913299849167507310"},
    "CZ": {"phone_code": "420", "name": "Czechia", "id": "5911198691036764307"},
    "CL": {"phone_code": "56", "name": "Chile", "id": "5911470957603592832"},
    "CO": {"phone_code": "57", "name": "Colombia", "id": "5913773060074246009"},
    "BI": {"phone_code": "257", "name": "Burundi", "id": "5913766441529642752"},
    "BW": {"phone_code": "267", "name": "Botswana", "id": "5911513782722499475"},
    "BA": {"phone_code": "387", "name": "Bosnia and Herzegovina", "id": "5913700002680541032"},
    "BO": {"phone_code": "591", "name": "Bolivia", "id": "5913638795101606133"},
    "BT": {"phone_code": "975", "name": "Bhutan", "id": "5913236734623093021"},
    "BJ": {"phone_code": "229", "name": "Benin", "id": "5913735869952430547"},
    "AR": {"phone_code": "54", "name": "Argentina", "id": "5913573356979884082"},
    "AU": {"phone_code": "61", "name": "Australia", "id": "5913632326880858455"},
    "AT": {"phone_code": "43", "name": "Austria", "id": "5911338831524664592"},
    "BS": {"phone_code": "1", "name": "Bahamas", "id": "5911451643135660214"},
    "BH": {"phone_code": "973", "name": "Bahrain", "id": "5913581663446634403"},
    "BD": {"phone_code": "880", "name": "Bangladesh", "id": "5911365056594973179"},
    "BB": {"phone_code": "1", "name": "Barbados", "id": "5911016996740272263"},
    "BE": {"phone_code": "32", "name": "Belgium", "id": "5913529642802745141"},
    "BZ": {"phone_code": "501", "name": "Belize", "id": "5913355005137522807"},
    "AG": {"phone_code": "1", "name": "Antigua and Barbuda", "id": "5913389025573475085"},
    "AO": {"phone_code": "244", "name": "Angola", "id": "5913753316109586411"},
    "AD": {"phone_code": "376", "name": "Andorra", "id": "5911314702398396902"},
    "DZ": {"phone_code": "213", "name": "Algeria", "id": "5913782968563800236"},
    "AL": {"phone_code": "355", "name": "Albania", "id": "5911357458797826163"},
    "AF": {"phone_code": "93", "name": "Afghanistan", "id": "5913492040364068694"},
    "ZW": {"phone_code": "263", "name": "Zimbabwe", "id": "5911092502265336396"},
    "CU": {"phone_code": "53", "name": "Cuba", "id": "5431551436502611633"},
    "KP": {"phone_code": "850", "name": "Korea", "id": "5434142701941437163"},
    "VE": {"phone_code": "58", "name": "Venezuela", "id": "5434009132753499322"},
    "SY": {"phone_code": "963", "name": "Syria", "id": "5433910876786670092"},
    "MM": {"phone_code": "95", "name": "Myanmar", "id": "5433666360003540231"},
    "NI": {"phone_code": "505", "name": "Nicaragua", "id": "5334807849418003620"},
    "KR": {"phone_code": "82", "name": "South Korea", "id": "5913371673905598425"},
    "GQ": {"phone_code": "240", "name": "Equatorial Guinea", "id": "5911306279967529251"},
    "GL": {"phone_code": "299", "name": "Greenland", "id": "5292014752283774878"},
    "FO": {"phone_code": "298", "name": "Faroe Islands", "id": "5296469342039327674"},
    "CI": {"phone_code": "225", "name": "Côte d'Ivoire (Ivory Coast)", "id": "5222233374948602940"},
    "BN": {"phone_code": "673", "name": "Brunei", "id": "5911336409163109113"},
    "BG": {"phone_code": "359", "name": "Bulgaria", "id": "5294329219965272288"},
    "BF": {"phone_code": "226", "name": "Burkina Faso", "id": "5913407764515786948"},
    "ER": {"phone_code": "291", "name": "Eritrea", "id": "5433723401464198287"},
    "MW": {"phone_code": "265", "name": "Malawi", "id": "5433968339154122439"},
    "MR": {"phone_code": "222", "name": "Mauritania", "id": "5433859405898594234"},
    "NR": {"phone_code": "674", "name": "Nauru", "id": "5434131139889478358"},
    "SA": {"phone_code": "966", "name": "Saudi Arabia", "id": "4985897134424328239"},
    "TO": {"phone_code": "676", "name": "Tonga", "id": "5433640100573491806"},
    "TV": {"phone_code": "688", "name": "Tuvalu", "id": "5433684690923961019"},
    "TW": {"phone_code": "886", "name": "Taiwan", "id": "5366187256937726720"},
    "HK": {"phone_code": "852", "name": "Hong Kong", "id": "5292166459118606932"},
    "MO": {"phone_code": "853", "name": "Macau", "id": "6323557758096377611"},
    "AI": {"phone_code": "1", "name": "Anguilla", "id": "5780471598922337683"},
    "AW": {"phone_code": "297", "name": "Aruba", "id": "5780471598922337683"},
    "VG": {"phone_code": "1", "name": "British Virgin Islands", "id": "5780471598922337683"},
    "KY": {"phone_code": "1", "name": "Cayman Islands", "id": "5780471598922337683"},
    "CW": {"phone_code": "599", "name": "Curacao", "id": "5780471598922337683"},
    "FK": {"phone_code": "500", "name": "Falkland Islands", "id": "5780471598922337683"},
    "GF": {"phone_code": "594", "name": "French Guiana", "id": "5780471598922337683"},
    "GP": {"phone_code": "590", "name": "Guadeloupe", "id": "5780471598922337683"},
    "GU": {"phone_code": "1", "name": "Guam", "id": "5780471598922337683"},
    "YT": {"phone_code": "262", "name": "Mayotte", "id": "5780471598922337683"},
    "MS": {"phone_code": "1", "name": "Montserrat", "id": "5780471598922337683"},
    "NC": {"phone_code": "687", "name": "New Caledonia", "id": "5780471598922337683"},
    "NU": {"phone_code": "683", "name": "Niue", "id": "5780471598922337683"},
    "NF": {"phone_code": "672", "name": "Norfolk Island", "id": "5780471598922337683"},
    "MP": {"phone_code": "1", "name": "Northern Mariana Islands", "id": "5780471598922337683"},
    "PN": {"phone_code": "64", "name": "Pitcairn Islands", "id": "5780471598922337683"},
    "RE": {"phone_code": "262", "name": "Reunion", "id": "5780471598922337683"},
    "SH": {"phone_code": "290", "name": "Saint Helena", "id": "5780471598922337683"},
    "TK": {"phone_code": "690", "name": "Tokelau", "id": "5780471598922337683"},
    "TC": {"phone_code": "1", "name": "Turks and Caicos Islands", "id": "5780471598922337683"},
    "VI": {"phone_code": "1", "name": "US Virgin Islands", "id": "5780471598922337683"},
    "WF": {"phone_code": "681", "name": "Wallis and Futuna", "id": "5780471598922337683"},
    "CK": {"phone_code": "682", "name": "Cook Islands", "id": "5780471598922337683"},
    "PF": {"phone_code": "689", "name": "French Polynesia", "id": "5780471598922337683"},
    "GI": {"phone_code": "350", "name": "Gibraltar", "id": "5780471598922337683"},
    "SJ": {"phone_code": "47", "name": "Svalbard and Jan Mayen", "id": "5780471598922337683"},
    "AX": {"phone_code": "358", "name": "Aland Islands", "id": "5780471598922337683"},
    "JE": {"phone_code": "44", "name": "Jersey", "id": "5780471598922337683"},
    "GG": {"phone_code": "44", "name": "Guernsey", "id": "5780471598922337683"},
    "IM": {"phone_code": "44", "name": "Isle of Man", "id": "5226538255029121667"},
    "PM": {"phone_code": "508", "name": "Saint Pierre and Miquelon", "id": "5780471598922337683"},
    "SX": {"phone_code": "1", "name": "Sint Maarten", "id": "5461113820955027461"},
    "BQ": {"phone_code": "599", "name": "Bonaire", "id": "5780471598922337683"}
}

def normalize_num(num_str):
    return re.sub(r'\D', '', str(num_str))

def resolve_country_name_and_code(input_str, sample_number=None):
    if not input_str and sample_number:
        clean_num = normalize_num(sample_number)
        for code, info in sorted(RAW_FLAG_EMOJIS.items(), key=lambda x: len(x[1]["phone_code"]), reverse=True):
            p_code = info["phone_code"]
            if p_code != "?" and clean_num.startswith(p_code):
                return info["name"], code
        return "Global", "US"

    if not input_str:
        return "Global", "US"

    clean_in = input_str.strip().upper()
    if clean_in in RAW_FLAG_EMOJIS:
        return RAW_FLAG_EMOJIS[clean_in]["name"], clean_in
    for code, info in RAW_FLAG_EMOJIS.items():
        if info["name"].upper() == clean_in:
            return info["name"], code
    for code, info in RAW_FLAG_EMOJIS.items():
        if clean_in in info["name"].upper():
            return info["name"], code
            
    if sample_number:
        clean_num = normalize_num(sample_number)
        for code, info in sorted(RAW_FLAG_EMOJIS.items(), key=lambda x: len(x[1]["phone_code"]), reverse=True):
            p_code = info["phone_code"]
            if p_code != "?" and clean_num.startswith(p_code):
                return info["name"], code

    return input_str.capitalize(), "US"

def get_flag_emoji_tag(country_name):
    _, code = resolve_country_name_and_code(country_name)
    if code in RAW_FLAG_EMOJIS:
        fid = RAW_FLAG_EMOJIS[code]["id"]
        return f'<tg-emoji emoji-id="{fid}"></tg-emoji>'
    return PEM["world"]

def get_country_code_prefix(country_name):
    _, code = resolve_country_name_and_code(country_name)
    if code in RAW_FLAG_EMOJIS:
        return RAW_FLAG_EMOJIS[code]["phone_code"]
    return ""

# =========================================================================
# --- COMPREHENSIVE MULTI-LANGUAGE DETECTOR ---
# =========================================================================
def detect_language_code(text):
    if not text:
        return "Global", "INT"
    lower_t = text.lower()
    
    if any(0x1200 <= ord(char) <= 0x137F for char in text):
        return "Amharic", "AM"
    if any(0x0980 <= ord(char) <= 0x09FF for char in text):
        return "Bengali", "BD"
    if any(c in lower_t for c in ['ê', 'î', 'û', 'ç', 'ş', 'ẍ', 'ḧ', 'ڤ', 'چ', 'پ', 'گ', 'ژ', 'kurmancî', 'سۆرانی', 'badînî', 'zazaki']):
        return "Kurdish", "KU"
    if any(ord(char) >= 0x4e00 and ord(char) <= 0x9fa5 for char in text):
        return "Chinese", "CN"
    elif any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in text):
        if any(w in lower_t for w in ['български', 'област', 'код']):
            return "Bulgarian", "BG"
        elif any(w in lower_t for w in ['македонски', 'јазик']):
            return "Macedonian", "MK"
        elif any(w in lower_t for w in ['українська', 'мова']):
            return "Ukrainian", "UA"
        elif any(w in lower_t for w in ['қазақ', 'тілі']):
            return "Kazakh", "KZ"
        elif any(w in lower_t for w in ['кыргыз']):
            return "Kyrgyz", "KG"
        elif any(w in lower_t for w in ['тоҷикӣ']):
            return "Tajik", "TJ"
        elif any(w in lower_t for w in ['монгол']):
            return "Mongolian", "MN"
        elif any(w in lower_t for w in ['српски']):
            return "Serbian", "RS"
        return "Russian", "RU"
    elif any(ord(char) >= 0x10A0 and ord(char) <= 0x10FF for char in text):
        return "Georgian", "GE"
    elif any(ord(char) >= 0x0600 and ord(char) <= 0x06FF for char in text):
        if any(w in lower_t for w in ['فارسی', 'زبان فارسی']):
            return "Persian", "IR"
        elif any(w in lower_t for w in ['اردو']):
            return "Urdu", "UR"
        elif any(w in lower_t for w in ['oʻzbek', 'ўзбек', 'o‘zbek']):
            return "Uzbek", "UZ"
        return "Arabic", "AR"
    elif any(ord(char) >= 0x0370 and ord(char) <= 0x03FF for char in text):
        return "Greek", "GR"
    elif any(ord(char) >= 0x0590 and ord(char) <= 0x05FF for char in text):
        return "Hebrew", "HE"
    elif any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in text):
        return "Hindi", "HI"
    elif any(ord(char) >= 0x0A80 and ord(char) <= 0x0AFF for char in text):
        return "Gujarati", "GU"
    elif any(ord(char) >= 0x0B80 and ord(char) <= 0x0BFF for char in text):
        return "Tamil", "TA"
    elif any(ord(char) >= 0x0D80 and ord(char) <= 0x0DFF for char in text):
        return "Sinhala", "SI"
    elif any(ord(char) >= 0x0E00 and ord(char) <= 0x0E7F for char in text):
        if any(w in lower_t for w in ['ລາວ', 'ภาษาลาว']):
            return "Lao", "LO"
        return "Thai", "TH"
    elif any(ord(char) >= 0x1780 and ord(char) <= 0x17FF for char in text):
        return "Khmer", "KM"
    elif any(ord(char) >= 0x1000 and ord(char) <= 0x109F for char in text):
        return "Burmese", "MY"
    elif any( (0x3040 <= ord(char) <= 0x309F) or (0x30A0 <= ord(char) <= 0x30FF) for char in text):
        return "Japanese", "JP"
    elif any(0xAC00 <= ord(char) <= 0xD7A3 for char in text):
        return "Korean", "KR"

    if any(w in lower_t for w in ['af soomaali']):
        return "Somali", "SO"
    elif any(w in lower_t for w in ['kiswahili']):
        return "Swahili", "SW"
    elif any(w in lower_t for w in ['lingála']):
        return "Lingala", "LN"
    elif any(w in lower_t for w in ['code de verification', 'vérification', 'compte', 'connexion', 'veuillez', 'identifiants', 'succ', 'français', 'kreyòl']):
        return "French", "FR"
    elif any(w in lower_t for w in ['deutsch', 'bestätigungscode', 'passwort', 'anmelden']):
        return "German", "DE"
    elif any(w in lower_t for w in ['język polski', 'kod weryfikacyjny', 'konto', 'hasło', 'polski']):
        return "Polish", "PL"
    elif any(w in lower_t for w in ['limba română', 'cod de verificare', 'cont', 'autentificare', 'română']):
        return "Romanian", "RO"
    elif any(w in lower_t for w in ['český jazyk', 'ověřovací kód', 'účet', 'přihlásit', 'český', 'bosanski']):
        return "Czech", "CZ"
    elif any(w in lower_t for w in ['svenska', 'verifieringskod', 'konto', 'logga in']):
        return "Swedish", "SE"
    elif any(w in lower_t for w in ['italiano', 'codice di verifica', 'accesso', 'account']):
        return "Italian", "IT"
    elif any(w in lower_t for w in ['español', 'código de verificación', 'cuenta', 'ingresar', 'mexicano']):
        return "Spanish", "ES"
    elif any(w in lower_t for w in ['türk dili', 'türkçe', 'doğrulama kodu', 'hesap', 'giriş', 'zazaki']):
        return "Turkish", "TR"
    elif any(w in lower_t for w in ['slovenský jazyk', 'overovací kód', 'účet', 'slovenčin']):
        return "Slovak", "SK"
    elif any(w in lower_t for w in ['slovenščina']):
        return "Slovenian", "SL"
    elif any(w in lower_t for w in ['língua portuguesa', 'português', 'código de verificação', 'conta', 'brasil']):
        return "Portuguese", "PT"
    elif any(w in lower_t for w in ['dansk', 'bekræftelseskode', 'konto']):
        return "Danish", "DK"
    elif any(w in lower_t for w in ['eesti', 'kinnituskood', 'konto', 'eesti keel']):
        return "Estonian", "EE"
    elif any(w in lower_t for w in ['suomi', 'vahvistuskoodi', 'tili']):
        return "Finnish", "FI"
    elif any(w in lower_t for w in ['hrvatski jezik', 'verifikacijski kod', 'račun', 'hrvatski']):
        return "Croatian", "HR"
    elif any(w in lower_t for w in ['magyar', 'ellenőrző kód', 'fiók', 'magyar nyelv']):
        return "Hungarian", "HU"
    elif any(w in lower_t for w in ['indonesia', 'bahasa indonesia', 'kode', 'verifikasi', 'masuk', 'kata', 'rahasia', 'akun']):
        return "Indonesian", "ID"
    elif any(w in lower_t for w in ['melayu', 'bahasa melayu']):
        return "Malay", "MS"
    elif any(w in lower_t for w in ['filipino', 'tagalog']):
        return "Filipino", "PH"
    elif any(w in lower_t for w in ['tiếng việt']):
        return "Vietnamese", "VI"
    elif any(w in lower_t for w in ['norsk']):
        return "Norwegian", "NB"
    elif any(w in lower_t for w in ['lietuvių', 'lietuvių kalba']):
        return "Lithuanian", "LT"
    elif any(w in lower_t for w in ['latviešu']):
        return "Latvian", "LV"
    elif any(w in lower_t for w in ['shqip']):
        return "Albanian", "AL"
    elif any(w in lower_t for w in ['íslenska']):
        return "Icelandic", "IS"
    elif any(w in lower_t for w in ['code', 'verification', 'password', 'login', 'security', 'pin']):
        return "English", "EN"

    return "Global", "INT"

# =========================================================================
# --- LOCAL JSON DATABASE CONFIGURATION ---
# =========================================================================
DB_FILE = "local_database.json"

def load_local_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty DB file")
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading local DB: {e}")
    return {
        "users": {},
        "assignments": {},
        "withdrawals": {},
        "stock": {},
        "settings": {
            'otp_rate': '1.0',
            'min_withdraw': '1000',
            'global_cc_limit': '3',
            'usd_rate': '126.0',
            'auto_ban_status': 'on'
        },
        "country_rates": {},
        "country_limits": {},
        "processed_messages": {}
    }

def save_local_db():
    try:
        data = {
            "users": CACHE_USERS,
            "assignments": CACHE_ASSIGNMENTS,
            "withdrawals": CACHE_WITHDRAWALS,
            "stock": CACHE_STOCK,
            "settings": CACHE_SETTINGS,
            "country_rates": CACHE_RATES,
            "country_limits": CACHE_LIMITS,
            "processed_messages": CACHE_PROCESSED
        }
        tmp_file = f"{DB_FILE}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, DB_FILE)
    except Exception as e:
        logger.error(f"Error saving local DB: {e}")

db_data = load_local_db()

CACHE_USERS = db_data.get("users", {})
CACHE_STOCK = db_data.get("stock", {})
CACHE_ASSIGNMENTS = db_data.get("assignments", {})
CACHE_SETTINGS = db_data.get("settings", {})
CACHE_RATES = db_data.get("country_rates", {})
CACHE_LIMITS = db_data.get("country_limits", {})
CACHE_PROCESSED = db_data.get("processed_messages", {})
CACHE_WITHDRAWALS = db_data.get("withdrawals", {})
USER_COOLDOWN = {}
USER_CC_TOGGLE = {} 
USER_FETCH_COUNT = {}

otp_process_lock = asyncio.Lock()

# =========================================================================
# --- BOT CONFIGURATION & GLOBAL SETTINGS ---
# =========================================================================
ADMIN_IDS = [6138186135, 6726432804]
SUPER_ADMIN_ID = 6138186135
import base64

# Bot token is reconstructed from Base64 so it is not stored as a plain-text string.
TOKEN = base64.b64decode(
    'ODg5Mzg2'
    'NTQxNjpB'
    'QUdlY01N'
    'd2NTZ1VM'
    'dUg3cXc1'
    'aVpTX1pT'
    'dGkyUUZx'
    'Vmxobw=='
).decode()
TARGET_GROUP_IDS = [-1003783166578] 
WEBHOOK_PORT = int(os.environ.get("PORT", 8080)) 

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, connect=5.0, read=15.0), 
    limits=httpx.Limits(max_connections=500, max_keepalive_connections=100),
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }
)

def init_default_settings():
    defaults = {
        'otp_rate': '1.0',
        'min_withdraw': '1000',
        'global_cc_limit': '3',
        'usd_rate': '126.0',
        'auto_ban_status': 'on'
    }
    for k, v in defaults.items():
        if k not in CACHE_SETTINGS:
            CACHE_SETTINGS[k] = v
    save_local_db()

init_default_settings()

# =========================================================================
# --- CORE UTILITY HELPERS ---
# =========================================================================
async def get_config_val(key, default):
    return str(CACHE_SETTINGS.get(key, default))

async def set_config_val(key, value):
    CACHE_SETTINGS[key] = str(value)
    save_local_db()

def mask_username(name):
    if not name or name == "N/A": return "N/A"
    length = len(name)
    hide_len = max(1, int(length * 0.7))
    return name[:length - hide_len] + "..."

def mask_user_id(uid_str):
    if not uid_str: return "N/A"
    s_uid = str(uid_str)
    length = len(s_uid)
    hide_len = max(1, int(length * 0.7))
    return s_uid[:length - hide_len] + "..."

async def get_country_payout(country_name):
    resolved_name, _ = resolve_country_name_and_code(country_name)
    if resolved_name in CACHE_RATES:
        return float(CACHE_RATES[resolved_name])
    if country_name in CACHE_RATES:
        return float(CACHE_RATES[country_name])
    default_rate = await get_config_val('otp_rate', '1.0')
    return float(default_rate)

async def get_country_cc_limit(country_name):
    if country_name in CACHE_LIMITS:
        return int(CACHE_LIMITS[country_name])
    global_limit = await get_config_val('global_cc_limit', '3')
    return int(global_limit)

def parse_otp_body(text):
    if not text: return "Not found"
    
    if "identifiants" in text.lower() or "identifiant" in text.lower():
        match_id = re.search(r'(\d{8,12})', text)
        if match_id:
            return match_id.group(1)

    numeric_match = re.search(r'\b(\d{4,8})(?!\d)', text)
    if numeric_match: 
        return numeric_match.group(1)
        
    mixed_match = re.search(r'\b(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]{4,10}\b', text)
    if mixed_match:
        val = mixed_match.group(0)
        if not re.match(r'^\d+(st|nd|rd|th)$', val, re.IGNORECASE):
            return val
            
    return "Not found"

# =========================================================================
# --- STYLED INTERFACE SYSTEM WITH PREMIUM EMOJIS ---
# =========================================================================
def rich_btn(text, style=None, callback_data=None, url=None, copy_text=None, icon_emoji_id=None):
    btn = {"text": text}
    if style: btn["style"] = style 
    if callback_data: btn["callback_data"] = callback_data
    if url: btn["url"] = url
    if copy_text: btn["copy_text"] = {"text": copy_text}
    if icon_emoji_id: btn["icon_custom_emoji_id"] = icon_emoji_id
    return btn

async def send_rich_message(bot, chat_id, text, keyboard_rows, parse_mode='HTML', **kwargs):
    payload = {
        "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": keyboard_rows}
    }
    payload.update(kwargs)
    url = f"https://api.telegram.org/bot{bot.token}/sendMessage"
    try:
        resp = await http_client.post(url, json=payload)
        return resp.json()
    except Exception as e: logger.error(f"Dispatch failure: {e}")

async def edit_rich_message(bot, chat_id, message_id, text, keyboard_rows, parse_mode='HTML'):
    payload = {
        "chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": keyboard_rows}
    }
    url = f"https://api.telegram.org/bot{bot.token}/editMessageText"
    try:
        resp = await http_client.post(url, json=payload)
        return resp.json()
    except Exception as e: logger.error(f"Edit failure: {e}")

# =========================================================================
# --- KEYBOARD LAYOUT ARCHITECTURE ---
# =========================================================================
def build_admin_main(uid):
    # ReplyKeyboardMarkup requires KeyboardButton objects/strings; the old
    # version passed Telegram Bot API dicts here, which causes PTB errors.
    rows = [
        [KeyboardButton("Number Upload"), KeyboardButton("Number Delete")],
        [KeyboardButton("User List"), KeyboardButton("Withdraw Requests")],
        [KeyboardButton("Admin Settings"), KeyboardButton("Broadcast")],
    ]
    if uid == SUPER_ADMIN_ID:
        rows.append([KeyboardButton("Upload User Data")])
    rows.append([KeyboardButton("/start")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def build_user_main():
    rows = [
        [KeyboardButton("Get Number 3"), KeyboardButton("Get Number 10")],
        [KeyboardButton("My Balance"), KeyboardButton("Withdraw Funds")],
        [KeyboardButton("Leaderboard"), KeyboardButton("Stock History")],
        [KeyboardButton("/start")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# =========================================================================
# --- ASSIGNED NUMBER AUTO-DELETE TIMER (2 HOURS) ---
# =========================================================================
async def auto_delete_assigned_number(assign_key):
    await asyncio.sleep(7200)
    if assign_key in CACHE_ASSIGNMENTS:
        del CACHE_ASSIGNMENTS[assign_key]
        save_local_db()

# =========================================================================
# --- USER STOCK ALLOCATION (FIFO ROTATION: MAXIMUM 20 ACTIVE NUMBERS) ---
# =========================================================================
async def engine_assign_batch(user_id, country_name, count=3):
    try:
        resolved_country, _ = resolve_country_name_and_code(country_name)
        now_ts = datetime.now().timestamp()
        
        user_info_fetch = USER_FETCH_COUNT.get(user_id, {'count': 0, 'last_time': 0.0})
        if user_info_fetch['count'] >= 2:
            elapsed = now_ts - user_info_fetch['last_time']
            if elapsed < 60:
                left = int(60 - elapsed)
                return None, f"⏳ আপনি পরপর ২ বার নাম্বার নিয়েছেন! দয়া করে আরও {left} সেকেন্ড অপেক্ষা করুন।"
            else:
                USER_FETCH_COUNT[user_id] = {'count': 0, 'last_time': now_ts}

        # Find all active numbers assigned to this user, sorted by assigned timestamp (oldest first)
        user_active_assignments = [
            (as_k, as_v) for as_k, as_v in CACHE_ASSIGNMENTS.items()
            if isinstance(as_v, dict) and as_v.get('user_id') == user_id and as_v.get('status') == 'assigned'
        ]
        user_active_assignments.sort(key=lambda x: x[1].get('assigned_at', ''))

        # If adding `count` new numbers exceeds maximum 20 limit, remove exactly the oldest batch (FIFO)
        total_after_add = len(user_active_assignments) + count
        if total_after_add > 20:
            excess_to_remove = total_after_add - 20
            # Remove the oldest assigned numbers to make room for new ones
            for i in range(min(excess_to_remove, len(user_active_assignments))):
                old_key = user_active_assignments[i][0]
                if old_key in CACHE_ASSIGNMENTS:
                    del CACHE_ASSIGNMENTS[old_key]

        assigned_numbers = []
        ts_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for batch_id, b_data in list(CACHE_STOCK.items()):
            b_country = b_data.get("country", "")
            r_b_country, _ = resolve_country_name_and_code(b_country)
            if isinstance(b_data, dict) and (r_b_country.upper() == resolved_country.upper() or b_country.upper() == country_name.upper()) and b_data.get("numbers"):
                nums = b_data.get("numbers", [])
                if not nums: continue
                take_count = min(count - len(assigned_numbers), len(nums))
                taken = nums[:take_count]
                b_data["numbers"] = nums[take_count:]
                assigned_numbers.extend(taken)
                if len(assigned_numbers) >= count:
                    break

        if not assigned_numbers:
            return None, "⚠️ Selected region stock empty!"

        current_cnt = user_info_fetch['count'] + 1
        USER_FETCH_COUNT[user_id] = {'count': current_cnt, 'last_time': datetime.now().timestamp()}

        num_data_list = []
        for num in assigned_numbers:
            clean = normalize_num(num)
            num_data_list.append({"full": clean})
            
            assign_key = f"as_{clean}_{user_id}"
            CACHE_ASSIGNMENTS[assign_key] = {
                'user_id': user_id,
                'number': clean,
                'country': resolved_country,
                'assigned_at': ts_now,
                'status': 'assigned'
            }
            asyncio.create_task(auto_delete_assigned_number(assign_key))

        save_local_db()
        return {"header": f"Numbers Assigned for {resolved_country}:", "numbers": num_data_list, "start_time": ts_now}, None
    except Exception as e:
        logger.error(f"Assignment core failure: {e}")
        return None, "💥 Allocation process fail!"

# =========================================================================
# --- SIGNAL PROCESSING & AUTO-BAN CHECK ---
# =========================================================================
processed_ids = set()
recent_sms_ids = {}

async def engine_process_signal(application, record, is_demo=False, demo_uid=None):
    async with otp_process_lock:
        r_num = str(record.get('to', record.get('called_number', record.get('num', record.get('number', '1234567890')))))
        r_msg = record.get('message', record.get('smstext', record.get('content', record.get('text', 'Code de verification: 98765'))))
        r_cli = record.get('senderid', record.get('cli', record.get('service', record.get('app', record.get('name', record.get('from', 'eBay'))))))
        
        if not is_demo:
            if not r_num or not r_msg: return False
            sms_id = str(record.get('smsid', record.get('id', '')))
            if sms_id and sms_id in recent_sms_ids:
                return False
                
            n_clean = normalize_num(r_num)
            m_hash = hashlib.md5(f"{n_clean}_{r_msg}".encode()).hexdigest()
            
            if m_hash in processed_ids:
                return False
        else:
            n_clean = "1234567890"
            m_hash = f"demo_{datetime.now().timestamp()}"

        try:
            matched_assign = None
            assigned_region = "Algeria" if is_demo else "Global"
            
            if not is_demo:
                for as_key, as_data in CACHE_ASSIGNMENTS.items():
                    if isinstance(as_data, dict) and as_data.get('status') == 'assigned':
                        as_num = normalize_num(as_data.get('number', ''))
                        if as_num.endswith(n_clean[-8:]) if len(n_clean) >= 8 else as_num == n_clean:
                            matched_assign = as_data
                            assigned_region = as_data.get('country', 'Global')
                            break

            flag_tag = get_flag_emoji_tag(assigned_region)
            otp_code = parse_otp_body(r_msg)
            escaped_body = html.escape(r_msg)
            lang_name, lang_code = detect_language_code(r_msg)
            if is_demo:
                lang_code = "FR"

            # Button with ONLY the OTP code
            kb = [
                [rich_btn(f"{otp_code}", style="primary", copy_text=otp_code, icon_emoji_id="5352862640592949843")]
            ]

            if is_demo:
                masked_name = mask_username("AdminDemoUser")
                masked_uid = mask_user_id(str(demo_uid))
                formatted_notif_text = (
                    f"{flag_tag} {PEM['new_em']} <code>{r_num}</code> {PEM['top_em']} <b>{lang_code}</b>\n\n"
                    f"{PEM['srv_em']} <b>Service:</b> <code>{r_cli}</code>\n"
                    f"{PEM['msg_em']} <b>Message:</b> <code>{escaped_body}</code>\n\n"
                    f"{PEM['user']} <b>User:</b> {masked_name} ({masked_uid})"
                )
                for gid in TARGET_GROUP_IDS:
                    try: await send_rich_message(application.bot, gid, formatted_notif_text, kb)
                    except: pass
                try: await send_rich_message(application.bot, SUPER_ADMIN_ID, f"🔔 <b>[Master Admin Demo Alert]</b>\n\n{formatted_notif_text}", kb)
                except: pass
                return True

            if matched_assign:
                u_id = matched_assign.get('user_id')
                u_data = CACHE_USERS.get(str(u_id), {}) if isinstance(CACHE_USERS.get(str(u_id)), dict) else {}
                if u_data.get('status') == 'banned': return False
                
                full_u_name = u_data.get('name', 'User')
                masked_name = mask_username(full_u_name)
                masked_uid = mask_user_id(u_id)

                formatted_notif_text = (
                    f"{flag_tag} {PEM['new_em']} <code>{r_num}</code> {PEM['top_em']} <b>{lang_code}</b>\n\n"
                    f"{PEM['srv_em']} <b>Service:</b> <code>{r_cli}</code>\n"
                    f"{PEM['msg_em']} <b>Message:</b> <code>{escaped_body}</code>\n\n"
                    f"{PEM['user']} <b>User:</b> {masked_name} ({masked_uid})"
                )

                u_msgs = CACHE_PROCESSED.get(str(u_id), {}) if isinstance(CACHE_PROCESSED.get(str(u_id)), dict) else {}
                
                if m_hash not in u_msgs:
                    processed_ids.add(m_hash)
                    payout = await get_country_payout(assigned_region)
                    
                    curr_bal = float(u_data.get('balance', 0.0))
                    curr_otp = int(u_data.get('otp_count', 0))
                    total = curr_bal + payout
                    
                    u_data.update({'balance': total, 'otp_count': curr_otp + 1})

                    if str(u_id) not in CACHE_PROCESSED or not isinstance(CACHE_PROCESSED[str(u_id)], dict):
                        CACHE_PROCESSED[str(u_id)] = {}
                    
                    CACHE_PROCESSED[str(u_id)][m_hash] = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    
                    auto_ban_status = await get_config_val('auto_ban_status', 'on')
                    if auto_ban_status.lower() == 'on':
                        seven_days_ago = datetime.now() - timedelta(days=7)
                        recent_7d_earnings = 0.0
                        for hm, hm_val in CACHE_PROCESSED[str(u_id)].items():
                            try:
                                t_dt = datetime.strptime(hm_val.get('timestamp'), '%Y-%m-%d %H:%M:%S')
                                if t_dt >= seven_days_ago:
                                    recent_7d_earnings += payout
                            except:
                                pass

                        if curr_otp >= 20 and recent_7d_earnings < 2000.0:
                            u_data['status'] = 'banned'
                            save_local_db()
                            ban_alert_msg = (
                                f"{PEM['warn']} <b>AUTO-BAN TRIGGERED</b> {PEM['warn']}\n\n"
                                f"👤 User: {full_u_name} (<code>{u_id}</code>)\n"
                                f"💵 Last 7 Days Earnings: Tk {recent_7d_earnings:.2f}\n"
                                f"🛡 Reason: Earnings below Tk 2000 limit in 7 days."
                            )
                            for aid in ADMIN_IDS:
                                try: await send_rich_message(application.bot, aid, ban_alert_msg, [])
                                except: pass
                            try: await send_rich_message(application.bot, u_id, f"{PEM['no']} <b>You have been automatically banned for low 7-day earnings threshold.</b>", [])
                            except: pass
                            return False

                    save_local_db()

                    for gid in TARGET_GROUP_IDS:
                        try: await send_rich_message(application.bot, gid, formatted_notif_text, kb)
                        except: pass
                    
                    user_inbox_alert = f"{formatted_notif_text}\n\nTk {payout:.2f} added to your balance!\n💳 Balance: Tk {total:.2f}"
                    try: await send_rich_message(application.bot, u_id, user_inbox_alert, kb)
                    except: pass
                    return True
            else:
                formatted_notif_text = (
                    f"{flag_tag} {PEM['new_em']} <code>{r_num}</code> {PEM['top_em']} <b>{lang_code}</b>\n\n"
                    f"{PEM['srv_em']} <b>Service:</b> <code>{r_cli}</code>\n"
                    f"{PEM['msg_em']} <b>Message:</b> <code>{escaped_body}</code>\n\n"
                    f"{PEM['user']} <b>User:</b> No user assigned"
                )
                for gid in TARGET_GROUP_IDS:
                    try: await send_rich_message(application.bot, gid, formatted_notif_text, kb)
                    except: pass
                return True
            return False
        except Exception as e:
            logger.error(f"Signal Routing Error: {e}")
            return False

# =========================================================================
# --- WEBHOOK SERVER ---
# =========================================================================
bot_application_instance = None

async def handle_postback(request):
    try:
        data = dict(request.query)
        if not data:
            try:
                data = await request.json()
            except:
                try:
                    data = dict(await request.post())
                except:
                    data = {}
        
        if data and bot_application_instance:
            asyncio.create_task(engine_process_signal(bot_application_instance, data))
            return web.Response(text="200 OK", status=200)
        return web.Response(text="Invalid payload", status=400)
    except Exception as e:
        logger.error(f"Postback error: {e}")
        return web.Response(text="Error", status=500)

async def start_webhook_server():
    app = web.Application()
    app.router.add_post('/webhook', handle_postback)
    app.router.add_get('/webhook', handle_postback)
    # Keep the old endpoint for backwards compatibility.
    app.router.add_post('/postback', handle_postback)
    app.router.add_get('/postback', handle_postback)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
        await site.start()
        logger.info(f"Direct Postback Webhook Server started on port {WEBHOOK_PORT}")
    except OSError as e:
        logger.error(f"Webhook port {WEBHOOK_PORT} could not be opened: {e}")
        await runner.cleanup()

# =========================================================================
# --- ROUTING & HANDLERS ENGINE ---
# =========================================================================
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    uid, name = user.id, user.full_name
    if user.username: name = f"@{user.username}"
    
    if uid not in ADMIN_IDS and await check_is_restricted(uid):
        await update.message.reply_text(f"{PEM['no']} <b>Access Restricted!</b>", parse_mode='HTML')
        return
    
    u_str = str(uid)
    if u_str not in CACHE_USERS or not isinstance(CACHE_USERS[u_str], dict):
        CACHE_USERS[u_str] = {'name': name, 'balance': 0.0, 'otp_count': 0, 'status': 'active'}
        save_local_db()
    else:
        CACHE_USERS[u_str]['name'] = name
        save_local_db()

    context.user_data['state'] = None
    if uid in ADMIN_IDS:
        await update.message.reply_text(f"{PEM['admin']} <b>Admin Control Active!</b>", reply_markup=build_admin_main(uid), parse_mode='HTML')
    else:
        await update.message.reply_text(f"{PEM['hi']} <b>Welcome {name}!</b>", reply_markup=build_user_main(), parse_mode='HTML')

async def router_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    if uid not in ADMIN_IDS and await check_is_restricted(uid): return

    if data == "select_country_menu":
        counts = {}
        for b_id, b_val in CACHE_STOCK.items():
            if isinstance(b_val, dict) and b_val.get('country'):
                c = b_val.get('country')
                r_c, _ = resolve_country_name_and_code(c)
                cnt = len(b_val.get('numbers', []))
                if cnt > 0: counts[r_c] = counts.get(r_c, 0) + cnt
        if not counts: 
            try: await query.answer("⚠️ Stock empty.", show_alert=True)
            except: pass
        else:
            try: await query.answer()
            except: pass
            btns = [[rich_btn(f"{c} ({cnt})", "primary", f"alloc_{c}", icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(c)[1], {}).get('id', "5780471598922337683"))] for c, cnt in counts.items()]
            btns.append([rich_btn("Return", "danger", "exit_session", icon_emoji_id="5422557736330106570")])
            await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['world']} <b>Select Region:</b>", btns)

    elif data.startswith("alloc_") or data == "change_num":
        region = data.replace("alloc_", "") if data.startswith("alloc_") else context.user_data.get('l_c')
        if not region: return
        resolved_region, _ = resolve_country_name_and_code(region)
        
        now_ts = datetime.now().timestamp()
        user_info_fetch = USER_FETCH_COUNT.get(uid, {'count': 0, 'last_time': 0.0})
        if user_info_fetch['count'] >= 2:
            elapsed = now_ts - user_info_fetch['last_time']
            if elapsed < 60:
                left = int(60 - elapsed)
                try:
                    await query.answer(f"⏳ আপনি পরপর ২ বার নাম্বার নিয়েছেন! দয়া করে আরও {left} সেকেন্ড অপেক্ষা করুন।", show_alert=True)
                except:
                    pass
                return

        context.user_data['l_c'] = resolved_region
        batch_size = context.user_data.get('p_count', 10)
        res, err = await engine_assign_batch(uid, resolved_region, batch_size)
        if err:
            try: await query.answer(err, show_alert=True)
            except: pass
        else:
            try: await query.answer()
            except: pass
            await render_active_numbers_message(context.bot, query.message.chat_id, query.message.message_id, uid, resolved_region, res)

    elif data == "toggle_cc":
        region = context.user_data.get('l_c', 'US')
        current_toggle = USER_CC_TOGGLE.get(uid, False)
        USER_CC_TOGGLE[uid] = not current_toggle
        
        assigned_nums = [v.get('number') for v in CACHE_ASSIGNMENTS.values() if isinstance(v, dict) and v.get('user_id') == uid and v.get('status') == 'assigned']
        if not assigned_nums:
            try: await query.answer("⚠️ No active numbers found.", show_alert=True)
            except: pass
            return
        
        res = {"header": f"Numbers Assigned for {region}:", "numbers": [{"full": n} for n in assigned_nums]}
        try: await query.answer()
        except: pass
        await render_active_numbers_message(context.bot, query.message.chat_id, query.message.message_id, uid, region, res)

    elif data == "exit_session":
        try: await query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=uid, text="🏁 Dashboard ready.", reply_markup=build_admin_main(uid) if uid in ADMIN_IDS else build_user_main())

    elif data.startswith("adm_del_") and not data.startswith("adm_del_yes_"):
        if uid not in ADMIN_IDS: return
        reg = data.replace("adm_del_", "")
        kb = [
            [rich_btn("Yes, Delete", style="danger", callback_data=f"adm_del_yes_{reg}", icon_emoji_id="5352694861990501856")],
            [rich_btn("Cancel", style="primary", callback_data="exit_session", icon_emoji_id="5420130255174145507")]
        ]
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['warn']} <b>Delete stock for {reg}?</b>", kb)

    elif data.startswith("adm_del_yes_"):
        if uid not in ADMIN_IDS: return

        # IMPORTANT: callback is adm_del_yes_<country>.
        # The old code used replace("adm_del_", ""), which produced
        # "yes_<country>" and therefore never matched the real country.
        reg = data[len("adm_del_yes_"):]
        resolved_reg, resolved_code = resolve_country_name_and_code(reg)
        deleted_count = 0
        deleted_batches = 0

        for b_id, b_val in list(CACHE_STOCK.items()):
            if not isinstance(b_val, dict):
                continue

            stored_country = str(b_val.get("country", "")).strip()
            stored_resolved, stored_code = resolve_country_name_and_code(stored_country)

            if (stored_resolved.upper() == resolved_reg.upper()
                    or stored_code.upper() == resolved_code.upper()
                    or stored_country.upper() == reg.upper()):
                nums = b_val.get("numbers", [])
                if isinstance(nums, list):
                    deleted_count += len(nums)
                deleted_batches += 1
                del CACHE_STOCK[b_id]

        # Persist the deletion immediately.
        save_local_db()
        try:
            await query.answer(f"Deleted {deleted_count} numbers", show_alert=True)
        except Exception:
            pass
        await query.edit_message_text(
            f"{PEM['ok']} <b>Deleted {deleted_count} unused numbers</b> from <b>{html.escape(resolved_reg)}</b>.\n"
            f"Batches removed: {deleted_batches}",
            parse_mode='HTML'
        )

    elif data == "admin_menu_panel":
        if uid not in ADMIN_IDS: return
        current_ban_status = await get_config_val('auto_ban_status', 'on')
        ban_toggle_text = f"Auto Ban: {current_ban_status.upper()}"
        ban_toggle_style = "success" if current_ban_status.lower() == 'on' else "danger"

        kb = [
            [
                rich_btn("Ban / Unban", style="danger", callback_data="adm_sub_ban_menu", icon_emoji_id="5334807341109908955"),
                rich_btn("Balance Mgmt", style="success", callback_data="adm_sub_bal_menu", icon_emoji_id="5348469219761626211")
            ],
            [
                rich_btn("User Search", style="primary", callback_data="adm_sub_search_menu", icon_emoji_id="5463352748751753567"),
                rich_btn("Banned List", style="primary", callback_data="adm_sub_banned_list", icon_emoji_id="5352861489541714456")
            ],
            [
                rich_btn("Get Unused TXT", style="success", callback_data="adm_get_unused_txt", icon_emoji_id="5352721946054268944"),
                rich_btn("Get User List TXT", style="success", callback_data="adm_get_userlist_txt", icon_emoji_id="5352861489541714456")
            ],
            [
                rich_btn("Set Country Rates", style="primary", callback_data="adm_set_country_rate", icon_emoji_id="5348469219761626211"),
                rich_btn("Set USD Rate", style="success", callback_data="adm_set_usd_rate", icon_emoji_id="5348469219761626211")
            ],
            [
                rich_btn(ban_toggle_text, style=ban_toggle_style, callback_data="adm_toggle_autoban", icon_emoji_id="5336944168944047463"),
                rich_btn("Demo OTP", style="primary", callback_data="adm_demo_otp", icon_emoji_id="5337302974806922068")
            ],
            [rich_btn("Main Menu", style="danger", callback_data="exit_session", icon_emoji_id="5422557736330106570")]
        ]
        try: await query.answer()
        except: pass
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['gear']} <b>Advanced Admin Panel & Management:</b>", kb)

    elif data == "adm_demo_otp":
        if uid not in ADMIN_IDS: return
        try:
            await query.answer("🚀 Demo OTP sent to group & admin inbox!", show_alert=True)
        except:
            pass
        asyncio.create_task(engine_process_signal(context.application, {}, is_demo=True, demo_uid=uid))

    elif data == "adm_toggle_autoban":
        if uid not in ADMIN_IDS: return
        curr = await get_config_val('auto_ban_status', 'on')
        new_val = 'off' if curr.lower() == 'on' else 'on'
        await set_config_val('auto_ban_status', new_val)
        try: await query.answer(f"Auto Ban is now {new_val.upper()}", show_alert=True)
        except: pass
        
        current_ban_status = new_val
        ban_toggle_text = f"Auto Ban: {current_ban_status.upper()}"
        ban_toggle_style = "success" if current_ban_status.lower() == 'on' else "danger"
        kb = [
            [
                rich_btn("Ban / Unban", style="danger", callback_data="adm_sub_ban_menu", icon_emoji_id="5334807341109908955"),
                rich_btn("Balance Mgmt", style="success", callback_data="adm_sub_bal_menu", icon_emoji_id="5348469219761626211")
            ],
            [
                rich_btn("User Search", style="primary", callback_data="adm_sub_search_menu", icon_emoji_id="5463352748751753567"),
                rich_btn("Banned List", style="primary", callback_data="adm_sub_banned_list", icon_emoji_id="5352861489541714456")
            ],
            [
                rich_btn("Get Unused TXT", style="success", callback_data="adm_get_unused_txt", icon_emoji_id="5352721946054268944"),
                rich_btn("Get User List TXT", style="success", callback_data="adm_get_userlist_txt", icon_emoji_id="5352861489541714456")
            ],
            [
                rich_btn("Set Country Rates", style="primary", callback_data="adm_set_country_rate", icon_emoji_id="5348469219761626211"),
                rich_btn("Set USD Rate", style="success", callback_data="adm_set_usd_rate", icon_emoji_id="5348469219761626211")
            ],
            [
                rich_btn(ban_toggle_text, style=ban_toggle_style, callback_data="adm_toggle_autoban", icon_emoji_id="5336944168944047463"),
                rich_btn("Demo OTP", style="primary", callback_data="adm_demo_otp", icon_emoji_id="5337302974806922068")
            ],
            [rich_btn("Main Menu", style="danger", callback_data="exit_session", icon_emoji_id="5422557736330106570")]
        ]
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['gear']} <b>Advanced Admin Panel & Management:</b>", kb)

    elif data == "adm_set_usd_rate":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_SET_USD_RATE_VAL'
        curr_usd = await get_config_val('usd_rate', '126.0')
        await context.bot.send_message(chat_id=uid, text=f"💵 Enter new USD rate for Binance withdraw (Current: Tk {curr_usd}/$):", parse_mode='HTML')

    elif data == "adm_set_country_rate":
        if uid not in ADMIN_IDS: return
        countries = set()
        for v in CACHE_STOCK.values():
            if isinstance(v, dict) and v.get('country'):
                r_c, _ = resolve_country_name_and_code(v.get('country'))
                countries.add(r_c)
        if not countries:
            try: await query.answer("⚠️ No stock countries available.", show_alert=True)
            except: pass
            return
        kb = [[rich_btn(f"Set Rate: {c}", "primary", f"adm_rate_{c}")] for c in countries]
        kb.append([rich_btn("🔙 Back", "danger", "admin_menu_panel")])
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, "✍️ <b>Select Country to Set OTP Rate:</b>", kb)

    elif data.startswith("adm_rate_"):
        if uid not in ADMIN_IDS: return
        target_c = data.replace("adm_rate_", "")
        context.user_data['target_rate_country'] = target_c
        context.user_data['state'] = 'ADM_SET_COUNTRY_RATE_VAL'
        await context.bot.send_message(chat_id=uid, text=f"✍️ Enter new OTP rate for <b>{target_c}</b> (Current: {CACHE_RATES.get(target_c, await get_config_val('otp_rate', '1.0'))} Tk):", parse_mode='HTML')

    elif data == "adm_get_unused_txt":
        if uid not in ADMIN_IDS: return
        try:
            stream = StringIO()
            stream.write("📦 Unused Stock Numbers Export\n" + "="*40 + "\n\n")
            has_stock = False
            for b_id, b_val in CACHE_STOCK.items():
                if isinstance(b_val, dict) and b_val.get('numbers'):
                    c = b_val.get('country', 'Global')
                    r_c, _ = resolve_country_name_and_code(c)
                    nums = b_val.get('numbers', [])
                    if nums:
                        has_stock = True
                        stream.write(f"--- Country: {r_c} ---\n")
                        for n in nums:
                            stream.write(f"+{normalize_num(n)}\n")
                        stream.write("\n")
            if not has_stock:
                try: await query.answer("⚠️ No unused stock found.", show_alert=True)
                except: pass
                return
            bio = BytesIO(stream.getvalue().encode('utf-8'))
            bio.name = f"unused_stock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try: await query.answer()
            except: pass
            await context.bot.send_document(chat_id=uid, document=bio, caption=f"{PEM['ok']} <b>Unused numbers exported successfully.</b>", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Unused stock export error: {e}")

    elif data == "adm_get_userlist_txt":
        if uid not in ADMIN_IDS: return
        try:
            stream = StringIO()
            stream.write("👥 Registered Active Users Export\n" + "="*45 + "\n\n")
            for u_id, u_val in CACHE_USERS.items():
                if isinstance(u_val, dict):
                    name = u_val.get('name', 'N/A')
                    bal = u_val.get('balance', 0.0)
                    otps = u_val.get('otp_count', 0)
                    status = u_val.get('status', 'active')
                    stream.write(f"UID: {u_id} | Name: {name} | Balance: Tk {bal:.2f} | OTPs: {otps} | Status: {status}\n")
            bio = BytesIO(stream.getvalue().encode('utf-8'))
            bio.name = f"users_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try: await query.answer()
            except: pass
            await context.bot.send_document(chat_id=uid, document=bio, caption=f"{PEM['ok']} <b>User list exported successfully.</b>", parse_mode='HTML')
        except Exception as e:
            logger.error(f"User list export error: {e}")

    elif data == "adm_sub_ban_menu":
        if uid not in ADMIN_IDS: return
        kb = [
            [rich_btn("Ban User", style="danger", callback_data="adm_trigger_ban", icon_emoji_id="5334807341109908955")],
            [rich_btn("Unban User", style="success", callback_data="adm_trigger_unban", icon_emoji_id="5352694861990501856")],
            [rich_btn("Back", style="primary", callback_data="admin_menu_panel", icon_emoji_id="5422557736330106570")]
        ]
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, "⚙️ <b>Ban / Unban Management:</b>", kb)

    elif data == "adm_trigger_ban":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_BAN_U'
        await context.bot.send_message(chat_id=uid, text="🚫 Enter target UID to ban:", parse_mode='HTML')

    elif data == "adm_trigger_unban":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_UNBAN_U'
        await context.bot.send_message(chat_id=uid, text="✅ Enter target UID to unban:", parse_mode='HTML')

    elif data == "adm_sub_bal_menu":
        if uid not in ADMIN_IDS: return
        kb = [
            [rich_btn("Add Balance", style="success", callback_data="adm_trigger_add_bal", icon_emoji_id="5420323438508155202")],
            [rich_btn("Remove Balance", style="danger", callback_data="adm_trigger_rem_bal", icon_emoji_id="5870818207383686839")],
            [rich_btn("Back", style="primary", callback_data="admin_menu_panel", icon_emoji_id="5422557736330106570")]
        ]
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, "💰 <b>Balance Management:</b>", kb)

    elif data == "adm_trigger_add_bal":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_ADD_BAL'
        await context.bot.send_message(chat_id=uid, text="➕ Enter UID and Amount (Format: UID AMOUNT):", parse_mode='HTML')

    elif data == "adm_trigger_rem_bal":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_REM_BAL'
        await context.bot.send_message(chat_id=uid, text="➖ Enter UID and Amount (Format: UID AMOUNT):", parse_mode='HTML')

    elif data == "adm_sub_search_menu":
        if uid not in ADMIN_IDS: return
        context.user_data['state'] = 'ADM_USER_LOOKUP'
        await context.bot.send_message(chat_id=uid, text="🔍 Enter target User UID to check details (OTPs breakdown over last 7 days):", parse_mode='HTML')

    elif data == "adm_sub_banned_list":
        if uid not in ADMIN_IDS: return
        banned_users = [f"UID: <code>{u_id}</code> | Name: {html.escape(v.get('name', 'N/A'))}" for u_id, v in CACHE_USERS.items() if isinstance(v, dict) and v.get('status') == 'banned']
        txt = "🚫 <b>Banned Users List:</b>\n\n" + ("\n".join(banned_users) if banned_users else "No banned users.")
        kb = [[rich_btn("Back", style="primary", callback_data="admin_menu_panel")]]
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, txt, kb)

    elif data.startswith("adm_pay_acc_"):
        if uid not in ADMIN_IDS: return
        w_id = data.replace("adm_pay_acc_", "")
        if w_id in CACHE_WITHDRAWALS:
            CACHE_WITHDRAWALS[w_id]['status'] = 'accepted'
            save_local_db()
            await query.edit_message_text(f"{PEM['ok']} Req {w_id} Authorized.")

    elif data.startswith("adm_pay_rej_"):
        if uid not in ADMIN_IDS: return
        w_id = data.replace("adm_pay_rej_", "")
        if w_id in CACHE_WITHDRAWALS:
            w = CACHE_WITHDRAWALS[w_id]
            w['status'] = 'rejected'
            u_str = str(w.get('user_id'))
            if u_str in CACHE_USERS:
                CACHE_USERS[u_str]['balance'] = float(CACHE_USERS[u_str].get('balance', 0)) + float(w.get('amount', 0))
            save_local_db()
            await query.edit_message_text(f"{PEM['no']} Withdrawal rejected. Funds restored.")

    elif data.startswith("w_method_"):
        channel = data.replace("w_method_", "")
        context.user_data['w_method'] = channel
        context.user_data['state'] = 'IN_W_AMT'
        usd_rate = float(await get_config_val('usd_rate', '126.0'))
        
        if channel == "Binance":
            await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"Selected <b>Binance</b>.\n💵 Min: $0.42 (~Tk 50)\n\n<b>Enter amount in USD (e.g., 5 or 10):</b>", [])
        elif channel == "Bkash":
            limit = 1000.0
            await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"Selected <b>Bkash</b>.\n💵 Min: Tk {limit} (~${limit/usd_rate:.2f})\n\n<b>Enter amount in BDT:</b>", [])
        else:
            limit = 1000.0
            await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"Selected <b>Nagad</b>.\n💵 Min: Tk {limit} (~${limit/usd_rate:.2f})\n\n<b>Enter amount in BDT:</b>", [])

    elif data == "adm_total_paid_show":
        if uid not in ADMIN_IDS: return
        limit_date = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d %H:%M:%S')
        paid_users, total_sum = set(), 0.0
        for w in CACHE_WITHDRAWALS.values():
            if isinstance(w, dict) and w.get('status') == 'accepted' and w.get('timestamp', '') >= limit_date:
                paid_users.add(w.get('user_id'))
                total_sum += float(w.get('amount', 0.0))
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['money']} <b>Total Paid (Last 6 Days)</b>\n\nUsers: {len(paid_users)}\nTotal: Tk {total_sum:.2f}", [[rich_btn("Back", style="primary", callback_data="exit_session")]])

    elif data == "adm_total_paid_clear":
        if uid not in ADMIN_IDS: return
        for w_id in [k for k, v in CACHE_WITHDRAWALS.items() if isinstance(v, dict) and v.get('status') == 'accepted']:
            del CACHE_WITHDRAWALS[w_id]
        save_local_db()
        await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, f"{PEM['ok']} History cleared.", [[rich_btn("Back", style="primary", callback_data="exit_session")]])

    elif data.startswith("vstock_"):
        await display_country_stock(update, context, data.replace("vstock_", ""))
    elif data.startswith("dlstock_"):
        await download_country_stock_file(update, context, data.replace("dlstock_", ""))
    elif data == "back_stock_hist":
        await dispatch_stock_history_menu(update, context, edit_message_id=query.message.message_id)

async def render_active_numbers_message(bot, chat_id, message_id, uid, region, res):
    resolved_region, _ = resolve_country_name_and_code(region)
    remove_cc = USER_CC_TOGGLE.get(uid, True)
    cc_prefix = get_country_code_prefix(resolved_region)
    flag_emoji = get_flag_emoji_tag(resolved_region)
    
    keyboard_rows = []
    for n in res['numbers']:
        full_num = n['full']
        display_num = full_num
        if remove_cc and cc_prefix and display_num.startswith(cc_prefix):
            display_num = display_num[len(cc_prefix):]
        
        btn_text = f"+{display_num}"
        copy_val = display_num
        keyboard_rows.append([rich_btn(btn_text, style="primary", copy_text=copy_val, icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(resolved_region)[1], {}).get('id', "5780471598922337683"))])

    cc_btn_text = "Add CC" if remove_cc else "Remove CC"
    cc_btn_style = "success" if remove_cc else "danger"
    keyboard_rows.append([rich_btn(cc_btn_text, style=cc_btn_style, callback_data="toggle_cc", icon_emoji_id="5420323438508155202" if remove_cc else "5422557736330106570")])

    keyboard_rows.append([rich_btn("Change Number", style="success", callback_data="change_num", icon_emoji_id="5352597830089347330")])
    keyboard_rows.append([rich_btn("Change Country", style="primary", callback_data="select_country_menu", icon_emoji_id="5336972142066047577")])

    text = f"{flag_emoji} <b>Waiting for OTP</b>\n\n{res['header']}"
    await edit_rich_message(bot, chat_id, message_id, text, keyboard_rows)

async def router_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    raw = msg.text.strip()
    uid = msg.from_user.id
    name = f"@{msg.from_user.username}" if msg.from_user.username else msg.from_user.full_name
    state = context.user_data.get('state')
    
    if uid not in ADMIN_IDS and await check_is_restricted(uid): return

    clean_raw = re.sub(r'[^\w\s]', '', raw).strip().lower()

    if raw == "/start":
        await handle_start(update, context)
        return

    if "user menu" in clean_raw:
        await msg.reply_text(f"{PEM['user']} <b>User Menu:</b>", reply_markup=build_user_main(), parse_mode='HTML')
        return

    if "get number 3" in clean_raw:
        context.user_data['p_count'] = 3
        counts = {}
        for b_val in CACHE_STOCK.values():
            if isinstance(b_val, dict) and b_val.get('country'):
                c = b_val.get('country')
                r_c, _ = resolve_country_name_and_code(c)
                cnt = len(b_val.get('numbers', []))
                if cnt > 0: counts[r_c] = counts.get(r_c, 0) + cnt
        if counts:
            btns = [[rich_btn(f"{c} ({cnt})", "primary", f"alloc_{c}", icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(c)[1], {}).get('id', "5780471598922337683"))] for c, cnt in counts.items()]
            await send_rich_message(context.bot, uid, f"{PEM['world']} <b>Select Region:</b>", btns)
        else: await msg.reply_text("⚠️ Inventory empty.")
        return
    elif "get number 10" in clean_raw:
        context.user_data['p_count'] = 10
        counts = {}
        for b_val in CACHE_STOCK.values():
            if isinstance(b_val, dict) and b_val.get('country'):
                c = b_val.get('country')
                r_c, _ = resolve_country_name_and_code(c)
                cnt = len(b_val.get('numbers', []))
                if cnt > 0: counts[r_c] = counts.get(r_c, 0) + cnt
        if counts:
            btns = [[rich_btn(f"{c} ({cnt})", "primary", f"alloc_{c}", icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(c)[1], {}).get('id', "5780471598922337683"))] for c, cnt in counts.items()]
            await send_rich_message(context.bot, uid, f"{PEM['world']} <b>Select Region:</b>", btns)
        else: await msg.reply_text("⚠️ Inventory empty.")
        return
    elif "my balance" in clean_raw:
        u_val = CACHE_USERS.get(str(uid), {})
        u_bal = float(u_val.get('balance', 0.0)) if isinstance(u_val, dict) else 0.0
        usd_rate = float(await get_config_val('usd_rate', '126.0'))
        await send_rich_message(context.bot, uid, f"💳 <b>Balance:</b> Tk {u_bal:.2f}\n💲 <b>USD:</b> $ {u_bal/usd_rate:.2f}", [])
        return
    elif "leaderboard" in clean_raw: 
        await dispatch_leaderboard(update)
        return
    elif "stock history" in clean_raw:
        await dispatch_stock_history_menu(update, context)
        return
    elif "withdraw funds" in clean_raw:
        kb = [
            [
                rich_btn("Bkash", style="primary", callback_data="w_method_Bkash", icon_emoji_id="6334668932980415143"),
                rich_btn("Nagad", style="success", callback_data="w_method_Nagad", icon_emoji_id="6334715949987404568")
            ],
            [
                rich_btn("Binance (USD)", style="primary", callback_data="w_method_Binance", icon_emoji_id="6334330042880893669")
            ]
        ]
        await send_rich_message(context.bot, uid, f"{PEM['gift']} <b>Select Payout Channel:</b>", kb)
        return

    if uid in ADMIN_IDS:
        if "number upload" in clean_raw:
            await msg.reply_text(f"{PEM['upload']} Enter country name or short code (e.g. Mali, ML, US, Bangladesh):"); context.user_data['state'] = 'ADM_UP_C'; return
        elif "number delete" in clean_raw: 
            await dispatch_wipe_ui(update, context); return 
        elif "user list" in clean_raw:
            await admin_export_user_db(update, context); return
        elif "withdraw requests" in clean_raw: 
            await dispatch_payout_ui(update, context); return
        elif "admin settings" in clean_raw:
            current_ban_status = await get_config_val('auto_ban_status', 'on')
            ban_toggle_text = f"Auto Ban: {current_ban_status.upper()}"
            ban_toggle_style = "success" if current_ban_status.lower() == 'on' else "danger"

            kb = [
                [
                    rich_btn("Ban / Unban", style="danger", callback_data="adm_sub_ban_menu", icon_emoji_id="5334807341109908955"),
                    rich_btn("Balance Mgmt", style="success", callback_data="adm_sub_bal_menu", icon_emoji_id="5348469219761626211")
                ],
                [
                    rich_btn("User Search", style="primary", callback_data="adm_sub_search_menu", icon_emoji_id="5463352748751753567"),
                    rich_btn("Banned List", style="primary", callback_data="adm_sub_banned_list", icon_emoji_id="5352861489541714456")
                ],
                [
                    rich_btn("Get Unused TXT", style="success", callback_data="adm_get_unused_txt", icon_emoji_id="5352721946054268944"),
                    rich_btn("Get User List TXT", style="success", callback_data="adm_get_userlist_txt", icon_emoji_id="5352861489541714456")
                ],
                [
                    rich_btn("Set Country Rates", style="primary", callback_data="adm_set_country_rate", icon_emoji_id="5348469219761626211"),
                    rich_btn("Set USD Rate", style="success", callback_data="adm_set_usd_rate", icon_emoji_id="5348469219761626211")
                ],
                [
                    rich_btn(ban_toggle_text, style=ban_toggle_style, callback_data="adm_toggle_autoban", icon_emoji_id="5336944168944047463"),
                    rich_btn("Demo OTP", style="primary", callback_data="adm_demo_otp", icon_emoji_id="5337302974806922068")
                ]
            ]
            await send_rich_message(context.bot, uid, f"{PEM['gear']} <b>Advanced Admin Panel & Management:</b>", kb); return
        elif "broadcast" in clean_raw:
            await msg.reply_text("📢 Enter message:"); context.user_data['state'] = 'ADM_BROAD'; return
        elif "upload user data" in clean_raw and uid == SUPER_ADMIN_ID:
            await msg.reply_text("📤 Send backup txt or json file:"); context.user_data['state'] = 'ADM_UP_USER_DB'; return

    if state == 'ADM_SET_USD_RATE_VAL':
        try:
            new_rate = float(raw)
            await set_config_val('usd_rate', str(new_rate))
            await msg.reply_text(f"{PEM['ok']} Binance USD rate updated to Tk {new_rate:.2f}/$", parse_mode='HTML')
        except Exception:
            await msg.reply_text(f"{PEM['no']} Invalid USD rate format.")
        context.user_data['state'] = None; return

    if state == 'ADM_UP_C':
        resolved_reg, _ = resolve_country_name_and_code(raw)
        context.user_data['temp_c'], context.user_data['state'] = resolved_reg, 'ADM_UP_F'
        await msg.reply_text(f"{PEM['ok']} Country resolved: <b>{resolved_reg}</b>.\n📥 Now upload inventory .txt file.", parse_mode='HTML'); return
    elif state == 'ADM_BROAD':
        asyncio.create_task(run_background_broadcast(context, raw))
        await msg.reply_text("📢 Broadcast started."); context.user_data['state'] = None; return
    elif state == 'ADM_BAN_U':
        t_id = raw.strip()
        if t_id in CACHE_USERS:
            if not isinstance(CACHE_USERS[t_id], dict):
                CACHE_USERS[t_id] = {'status': 'banned'}
            else:
                CACHE_USERS[t_id]['status'] = 'banned'
            save_local_db()
            await msg.reply_text(f"{PEM['ok']} User UID <code>{t_id}</code> has been banned successfully.", parse_mode='HTML')
        else:
            await msg.reply_text(f"{PEM['no']} User UID <code>{t_id}</code> not found in database.", parse_mode='HTML')
        context.user_data['state'] = None; return
    elif state == 'ADM_UNBAN_U':
        t_id = raw.strip()
        if t_id in CACHE_USERS:
            if not isinstance(CACHE_USERS[t_id], dict):
                CACHE_USERS[t_id] = {'status': 'active'}
            else:
                CACHE_USERS[t_id]['status'] = 'active'
            
            if t_id in CACHE_PROCESSED:
                CACHE_PROCESSED[t_id] = {}

            save_local_db()
            await msg.reply_text(f"{PEM['ok']} User UID <code>{t_id}</code> has been unbanned. Balance remains safe and 7-day timer reset.", parse_mode='HTML')
        else:
            await msg.reply_text(f"{PEM['no']} User UID <code>{t_id}</code> not found in database.", parse_mode='HTML')
        context.user_data['state'] = None; return
    elif state == 'ADM_SET_COUNTRY_RATE_VAL':
        try:
            target_c = context.user_data.get('target_rate_country')
            new_rate = float(raw)
            CACHE_RATES[target_c] = new_rate
            save_local_db()
            await msg.reply_text(f"{PEM['ok']} OTP Rate for <b>{target_c}</b> updated to Tk {new_rate:.2f}", parse_mode='HTML')
        except Exception:
            await msg.reply_text(f"{PEM['no']} Invalid rate format.")
        context.user_data['state'] = None; return
    elif state == 'ADM_ADD_BAL':
        try:
            parts = raw.split()
            t_id, add_amt = parts[0], float(parts[1])
            if t_id in CACHE_USERS:
                cur = float(CACHE_USERS[t_id].get('balance', 0.0))
                CACHE_USERS[t_id]['balance'] = cur + add_amt
                save_local_db()
                await msg.reply_text(f"{PEM['ok']} Added Tk {add_amt} to UID {t_id}. New Balance: Tk {CACHE_USERS[t_id]['balance']}")
            else:
                await msg.reply_text(f"{PEM['no']} UID not found.")
        except Exception:
            await msg.reply_text(f"{PEM['no']} Format error. Use: UID AMOUNT")
        context.user_data['state'] = None; return
    elif state == 'ADM_REM_BAL':
        try:
            parts = raw.split()
            t_id, rem_amt = parts[0], float(parts[1])
            if t_id in CACHE_USERS:
                cur = float(CACHE_USERS[t_id].get('balance', 0.0))
                CACHE_USERS[t_id]['balance'] = max(0.0, cur - rem_amt)
                save_local_db()
                await msg.reply_text(f"{PEM['ok']} Removed Tk {rem_amt} from UID {t_id}. New Balance: Tk {CACHE_USERS[t_id]['balance']}")
            else:
                await msg.reply_text(f"{PEM['no']} UID not found.")
        except Exception:
            await msg.reply_text(f"{PEM['no']} Format error. Use: UID AMOUNT")
        context.user_data['state'] = None; return
    elif state == 'ADM_USER_LOOKUP':
        t_id = raw.strip()
        if t_id in CACHE_USERS:
            u_info = CACHE_USERS[t_id]
            p_dict = CACHE_PROCESSED.get(t_id, {})
            now_dt = datetime.now()
            daily_breakdown = ""
            for i in range(7):
                day_target = (now_dt - timedelta(days=i)).strftime('%Y-%m-%d')
                cnt = sum(1 for m in p_dict.values() if isinstance(m, dict) and m.get('timestamp', '').startswith(day_target))
                daily_breakdown += f"• {day_target}: {cnt} OTPs\n"
            
            res_text = (
                f"{PEM['user']} <b>User Details for UID:</b> <code>{t_id}</code>\n"
                f"👤 Name: {html.escape(u_info.get('name', 'N/A'))}\n"
                f"💳 Balance: Tk {u_info.get('balance', 0.0):.2f}\n"
                f"📊 Total OTPs: {u_info.get('otp_count', 0)}\n"
                f"🛡 Status: {u_info.get('status', 'active')}\n\n"
                f"📅 <b>OTPs Breakdown (Last 7 Days):</b>\n{daily_breakdown}"
            )
            await msg.reply_text(res_text, parse_mode='HTML')
        else:
            await msg.reply_text(f"{PEM['no']} User UID not found.")
        context.user_data['state'] = None; return

    if state == 'IN_W_AMT':
        try:
            val_input = float(raw)
            method = context.user_data.get('w_method', 'Bkash')
            usd_rate = float(await get_config_val('usd_rate', '126.0'))
            
            if method == "Binance":
                amt = val_input * usd_rate
                min_usd = 50.0 / usd_rate
                if val_input < min_usd:
                    await msg.reply_text(f"❌ Minimum withdraw for Binance is ${min_usd:.2f} (~Tk 50)"); context.user_data['state'] = None; return
            else:
                amt = val_input
                limit = 1000.0
                if amt < limit:
                    await msg.reply_text(f"❌ Minimum withdraw for {method} is Tk {limit}"); context.user_data['state'] = None; return

            if float(CACHE_USERS.get(str(uid), {}).get('balance', 0)) < amt:
                await msg.reply_text("❌ Insufficient balance."); context.user_data['state'] = None; return
                
            context.user_data['temp_w_amt'] = amt
            context.user_data['state'] = 'IN_W_INFO'
            acc_prompt = "Binance UID / Email / Pay ID:" if method == "Binance" else f"{method} Account Number:"
            await msg.reply_text(f"📱 Enter your {acc_prompt}")
        except Exception as e:
            logger.error(f"Withdraw amount parse error: {e}")
            await msg.reply_text("❌ Invalid amount format.")
            context.user_data['state'] = None
        return
    elif state == 'IN_W_INFO':
        amt = context.user_data['temp_w_amt']
        u_str = str(uid)
        bal = float(CACHE_USERS.get(u_str, {}).get('balance', 0))
        usd_rate = float(await get_config_val('usd_rate', '126.0'))
        method = context.user_data.get('w_method', 'Bkash')
        
        if bal >= amt:
            ref = f"w_{int(datetime.now().timestamp())}"
            CACHE_WITHDRAWALS[ref] = {
                'user_id': uid, 'user_name': name, 'amount': amt, 'info': raw, 
                'method': method, 'status': 'pending', 
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            CACHE_USERS[u_str]['balance'] = bal - amt
            save_local_db()
            
            usd_amt = amt / usd_rate
            await msg.reply_text(f"✅ Withdraw request submitted!\n🛒 Method: {method}\n💵 Amount: Tk {amt:.2f} (~${usd_amt:.2f})\nRate: Tk {usd_rate}/$")
        else: 
            await msg.reply_text("❌ Insufficient balance.")
        context.user_data['state'] = None
        return

async def handler_file_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS: return
    state = context.user_data.get('state')
    
    if state == 'ADM_UP_USER_DB' and uid == SUPER_ADMIN_ID:
        try:
            doc = await update.message.document.get_file()
            path = f"tmp_{uid}.txt"
            await doc.download_to_drive(path)
            with open(path, "r", encoding='utf-8') as f: content = f.read()
            
            global CACHE_USERS
            imported_count = 0
            for line in content.splitlines():
                if "UID:" in line and "Balance:" in line:
                    try:
                        parts = [p.strip() for p in line.split("|")]
                        u_id_val = parts[0].replace("UID:", "").strip()
                        u_name_val = parts[1].replace("Name:", "").replace("Username:", "").strip()
                        u_bal_val = float(parts[2].replace("Balance:", "").replace("Earnings:", "").replace("Tk", "").strip())
                        u_otps_val = int(parts[3].replace("OTPs:", "").strip()) if len(parts) > 3 and "OTPs:" in parts[3] else 0
                        u_status_val = parts[4].replace("Status:", "").strip() if len(parts) > 4 and "Status:" in parts[4] else "active"
                        
                        CACHE_USERS[u_id_val] = {
                            "name": u_name_val,
                            "balance": u_bal_val,
                            "otp_count": u_otps_val,
                            "status": u_status_val
                        }
                        imported_count += 1
                    except Exception as parse_err:
                        logger.error(f"Line parse error: {parse_err}")
                        
            save_local_db()
            await update.message.reply_text(f"{PEM['ok']} Successfully imported {imported_count} users database!")
        except Exception as e: 
            await update.message.reply_text(f"{PEM['no']} Error: {e}")
        context.user_data['state'] = None; return

    if state != 'ADM_UP_F': return
    try:
        temp_input_country = context.user_data.get('temp_c', 'Unknown')
        doc = await update.message.document.get_file()
        path = f"tmp_sync_{uid}.txt"
        await doc.download_to_drive(path)
        with open(path, "r", encoding='utf-8') as f: nums = [l.strip() for l in f if l.strip()]
        
        sample_num = nums[0] if nums else None
        reg, _ = resolve_country_name_and_code(temp_input_country, sample_number=sample_num)
        
        # Include microseconds so two uploads in the same second cannot overwrite each other.
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        CACHE_STOCK[batch_id] = {
            "country": reg,
            "numbers": nums,
            "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # CRITICAL: stock must be persisted after every upload.
        save_local_db()

        await update.message.reply_text(f"{PEM['rocket']} Uploaded {len(nums)} numbers for <b>{reg}</b> (Auto-detected & Stored safely).", parse_mode='HTML')
    except Exception as e: await update.message.reply_text(f"{PEM['no']} Error: {e}")
    context.user_data['state'] = None

async def admin_export_user_db(update, context):
    try:
        if not CACHE_USERS:
            await update.effective_chat.send_message("⚠️ <b>User List Empty:</b> কোনো ইউজার রেজিস্টার্ড হয়নি।", parse_mode='HTML')
            return
            
        stream = StringIO()
        stream.write("👥 Registered Active User List\n" + "="*45 + "\n\n")
        
        user_count = 0
        for u_id, u_val in CACHE_USERS.items():
            if isinstance(u_val, dict) and int(u_id) not in ADMIN_IDS:
                status = u_val.get('status', 'active')
                if status == 'banned': continue
                    
                name = u_val.get('name', 'N/A')
                balance = float(u_val.get('balance', 0.0))
                otp_cnt = u_val.get('otp_count', 0)
                
                stream.write(f"UID: {u_id} | Name: {name} | Balance: Tk {balance:.2f} | OTPs: {otp_cnt} | Status: {status}\n")
                user_count += 1
            
        bio = BytesIO(stream.getvalue().encode('utf-8'))
        bio.name = f"active_user_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=bio, 
            caption=f"👥 <b>Total Active Users Exported:</b> {user_count}",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"User list export failed: {e}")
        await update.effective_chat.send_message(f"❌ <b>Export Error:</b> {e}", parse_mode='HTML')

async def dispatch_stock_history_menu(update, context, edit_message_id=None):
    uid = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    chat_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
    counts = {}
    for v in CACHE_ASSIGNMENTS.values():
        if isinstance(v, dict) and v.get('user_id') == uid and v.get('status') == 'assigned':
            c = v.get('country', 'Global')
            r_c, _ = resolve_country_name_and_code(c)
            counts[r_c] = counts.get(r_c, 0) + 1
    if not counts:
        text, kb = "📦 No active stock found.", [[rich_btn("Close", style="danger", callback_data="exit_session")]]
    else:
        text, kb = "📦 Select country to view stock:", [[rich_btn(f"{c} ({cnt})", "primary", callback_data=f"vstock_{c}", icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(c)[1], {}).get('id', "5780471598922337683"))] for c, cnt in counts.items()]
        kb.append([rich_btn("Close", style="danger", callback_data="exit_session")])
    if edit_message_id: await edit_rich_message(context.bot, chat_id, edit_message_id, text, kb)
    else: await send_rich_message(context.bot, uid, text, kb)

async def display_country_stock(update, context, country):
    query = update.callback_query
    uid = query.from_user.id
    resolved_country, _ = resolve_country_name_and_code(country)
    
    # Get active numbers for user and country, sorted by assignment time (newest on top or FIFO order)
    user_assignments = [
        v for v in CACHE_ASSIGNMENTS.values()
        if isinstance(v, dict) and v.get('user_id') == uid and resolve_country_name_and_code(v.get('country'))[0].upper() == resolved_country.upper() and v.get('status') == 'assigned'
    ]
    user_assignments.sort(key=lambda x: x.get('assigned_at', ''), reverse=True)
    nums = [v.get('number') for v in user_assignments][:20]  # Display up to 20 numbers in stock history view
    
    text = f"📦 Stock for {resolved_country} ({len(nums)} nos):\n\n" + "".join([f"• <code>+{normalize_num(n)}</code>\n" for n in nums])
    kb = [[rich_btn("Download .txt", style="success", callback_data=f"dlstock_{resolved_country}")], [rich_btn("Back", style="primary", callback_data="back_stock_hist")]]
    await edit_rich_message(context.bot, query.message.chat_id, query.message.message_id, text, kb)

async def download_country_stock_file(update, context, country):
    query = update.callback_query
    uid = query.from_user.id
    resolved_country, _ = resolve_country_name_and_code(country)
    
    user_assignments = [
        v for v in CACHE_ASSIGNMENTS.values()
        if isinstance(v, dict) and v.get('user_id') == uid and resolve_country_name_and_code(v.get('country'))[0].upper() == resolved_country.upper() and v.get('status') == 'assigned'
    ]
    user_assignments.sort(key=lambda x: x.get('assigned_at', ''), reverse=True)
    nums = [normalize_num(v.get('number')) for v in user_assignments][:20]
    
    stream = StringIO()
    for n in nums: stream.write(f"+{n}\n")
    bio = BytesIO(stream.getvalue().encode('utf-8'))
    bio.name = f"{resolved_country}_stock.txt"
    await context.bot.send_document(chat_id=uid, document=bio, caption=f"📄 Stock export for {resolved_country}")

async def run_background_broadcast(context, payload):
    for u_id in CACHE_USERS.keys():
        try: await send_rich_message(context.bot, int(u_id), f'📢 <b>Notice:</b>\n\n{payload}', []); await asyncio.sleep(0.035)
        except: pass

async def dispatch_payout_ui(update, context):
    pending = False
    usd_rate = float(await get_config_val('usd_rate', '126.0'))
    for w_id, w in CACHE_WITHDRAWALS.items():
        if isinstance(w, dict) and w.get('status') == 'pending':
            pending = True
            amt = float(w.get('amount', 0))
            usd_amt = amt / usd_rate
            kb = [
                [rich_btn("Copy Info", "primary", copy_text=str(w.get('info')))],
                [rich_btn("Authorize", "success", f"adm_pay_acc_{w_id}"), rich_btn("Reject", "danger", f"adm_pay_rej_{w_id}")]
            ]
            await send_rich_message(context.bot, update.message.chat_id, f"💸 <b>Withdraw Req</b>\nID: <code>{w_id}</code>\nName: {html.escape(w.get('user_name'))}\nAmount: Tk {amt:.2f} (~${usd_amt:.2f} @ {usd_rate}/$)\nMethod: {w.get('method')}\nInfo: <code>{w.get('info')}</code>", kb)
    if not pending: await update.message.reply_text("🏁 Withdraw queue empty.")

async def dispatch_wipe_ui(update, context):
    countries = set()
    for v in CACHE_STOCK.values():
        if isinstance(v, dict) and v.get('country'):
            r_c, _ = resolve_country_name_and_code(v.get('country'))
            countries.add(r_c)
    if countries: await send_rich_message(context.bot, update.message.chat_id, "🚨 <b>Purge stock:</b>", [[rich_btn(f"Purge: {c}", "danger", f"adm_del_{c}", icon_emoji_id=RAW_FLAG_EMOJIS.get(resolve_country_name_and_code(c)[1], {}).get('id', "5780471598922337683"))] for c in countries])
    else: await update.message.reply_text("⚠️ Inventory empty.")

async def dispatch_leaderboard(update):
    scores = {}
    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    for u_id, p in CACHE_PROCESSED.items():
        if isinstance(p, dict):
            cnt = sum(1 for m in p.values() if isinstance(m, dict) and m.get('timestamp', '') >= midnight)
            if cnt > 0: scores[u_id] = cnt
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_scores:
        out = f"{PEM['lb_head']} <b>Daily Ranking:</b>\n\n"
        for i, (u_id, score) in enumerate(sorted_scores[:10], 1):
            u_name = CACHE_USERS.get(str(u_id), {}).get('name', 'User')
            if i == 1:
                rank_em = PEM["lb_1"]
            elif i == 2:
                rank_em = PEM["lb_2"]
            elif i == 3:
                rank_em = PEM["lb_3"]
            elif i == 4:
                rank_em = PEM["lb_4"]
            elif i == 5:
                rank_em = PEM["lb_5"]
            elif i == 6:
                rank_em = PEM["lb_6"]
            elif i == 7:
                rank_em = PEM["lb_7"]
            elif i == 8:
                rank_em = PEM["lb_8"]
            elif i == 9:
                rank_em = PEM["lb_9"]
            else:
                rank_em = PEM["lb_10"]
            out += f"{rank_em} {mask_username(u_name)} - OTP: {score}\n"
        await update.message.reply_text(out, parse_mode='HTML')
    else: await update.message.reply_text("⏱️ No activity yet.")

async def check_is_restricted(uid):
    return CACHE_USERS.get(str(uid), {}).get('status') == 'banned'

async def app_post_init(app):
    global bot_application_instance
    bot_application_instance = app
    await start_webhook_server()
    logger.info("Direct Postback Webhook Engine initialized.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception occurred during live update cycle:", exc_info=context.error)

if __name__ == '__main__':
    try:
        instance = ApplicationBuilder().token(TOKEN).request(HTTPXRequest(connection_pool_size=8, read_timeout=20.0, write_timeout=20.0, connect_timeout=15.0)).post_init(app_post_init).build()
        instance.add_handler(CommandHandler("start", handle_start))
        instance.add_handler(CallbackQueryHandler(router_callbacks))
        instance.add_handler(MessageHandler(filters.Document.ALL, handler_file_up))
        instance.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), router_text))
        instance.add_error_handler(error_handler)
        
        logger.info("Terminal tactical build fully stabilized with custom country rates and auto name/flag resolution.")
        instance.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Panic Shutdown: {e}")
