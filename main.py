import json
import logging
import os
import re
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ROOT_ADMIN_UID = 6138186135
ADMIN_UIDS = {ROOT_ADMIN_UID}

USER_DATABASE = {}
ACTIVE_NUMBER_ALLOCATIONS = {} 

SERVICES = [] 
COUNTRY_PRICES = {} 
INBOX_NUMBERS = {} 
USER_PREFIXES = {}
USER_NUMBER_INDICES = {}

OTP_GROUP_CHAT_ID = "@PakistanOTPCommunity"

HTML_EMOJIS = {
    "money_bag": "<tg-emoji emoji-id='6190336264940559752'>💰</tg-emoji>",
    "user": "<tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji>",
    "balance": "<tg-emoji emoji-id='5776103539872896061'>💵</tg-emoji>",
    "paid": "<tg-emoji emoji-id='5395444784611480792'>📦</tg-emoji>",
    "referral": "<tg-emoji emoji-id='5334590977837403844'>👥</tg-emoji>",
    "otp": "<tg-emoji emoji-id='6093587384954262033'>📬</tg-emoji>",
    "warn": "<tg-emoji emoji-id='5336944168944047463'>⚠️</tg-emoji>",
    "fee": "<tg-emoji emoji-id='5895592588064328942'>💳</tg-emoji>",
    "card": "<tg-emoji emoji-id='5348469219761626211'>💳</tg-emoji>",
    "address": "<tg-emoji emoji-id='6215173330668884439'>📧</tg-emoji>"
}

RAW_APP_EMOJIS = {
    "whatsapp": {"id": "5100676158270211089"}, 
    "facebook": {"id": "5334807341109908955"}, 
    "telegram": {"id": "5337010556253543833"}, 
    "imo": {"id": "5337155807752524558"},
    "instagram": {"id": "5334868205091459431"}, 
    "apple": {"id": "5334637951894722661"},
    "google": {"id": "5335010201005231986"}, 
    "microsoft": {"id": "5334880948259427772"},
    "tiktok": {"id": "5339213256001102461"}, 
    "amazon": {"id": "4995019580536524226"},
    "paypal": {"id": "5776103539872896061"},
    "discord": {"id": "5116246243646898866"},
    "bkash": {"id": "5348469219761626211"}, 
    "rocket": {"id": "5352597830089347330"},
    "talabot": {"id": "5336879280578138635"}
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

def get_user_data(user_id):
    if user_id not in USER_DATABASE:
        USER_DATABASE[user_id] = {
            "balance": 0.0000,
            "total_paid": 0.0000,
            "referrals": 0,
            "otp_received": 0,
            "wallet": "Not Set"
        }
    return USER_DATABASE[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user_data(user_id)
    
    keyboard_layout = {
        "keyboard": [
            [
                {"text": "Get Number", "style": "success", "icon_custom_emoji_id": "5294193228415801857"},
                {"text": "Search Number", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}
            ],
            [
                {"text": "Live Traffic", "style": "success", "icon_custom_emoji_id": "6226744728478556191"},
                {"text": "Withdraw", "style": "danger", "icon_custom_emoji_id": "6190336264940559752"}
            ],
            [
                {"text": "Help", "style": "primary", "icon_custom_emoji_id": "5424905936684736034"}
            ]
        ],
        "resize_keyboard": True,
        "persistent": True,
        "placeholder": "Choose an option..."
    }
    
    if user_id in ADMIN_UIDS:
        keyboard_layout["keyboard"].append([
            {"text": "🛠️ Admin Panel", "style": "primary", "icon_custom_emoji_id": "5895592588064328942"}
        ])

    await update.message.reply_text(
        text='<tg-emoji emoji-id="5017470156276761427">🔄</tg-emoji> <b>Menu Refreshed Successfully!</b>',
        reply_markup=json.dumps(keyboard_layout),
        parse_mode="HTML"
    )

async def send_live_traffic(message_obj, is_edit=False):
    added_countries = set()
    for srv, countries in COUNTRY_PRICES.items():
        for c in countries:
            added_countries.add((c["code"], c["name"], c.get("id", "5294193228415801857")))

    if not added_countries:
        no_traffic_msg = "⚠️ <b>No countries added yet in admin panel.</b>"
        if is_edit:
            try:
                await message_obj.edit_text(text=no_traffic_msg, parse_mode="HTML")
            except Exception:
                pass
        else:
            await message_obj.reply_text(text=no_traffic_msg, parse_mode="HTML")
        return

    sorted_countries = sorted(list(added_countries), key=lambda x: x[1])
    top_country_name = sorted_countries[0][1]
    top_country_id = sorted_countries[0][2]

    traffic_header = (
        f"<tg-emoji emoji-id='6226744728478556191'>📊</tg-emoji> <b>Live Traffic</b>\n\n"
        f"📅 Window: Last 5 minutes\n"
        f"🏆 Results Sent: 100%\n"
        f"📌 Top Country: <tg-emoji emoji-id='{top_country_id}'>🌐</tg-emoji> {top_country_name}\n\n"
        f"🌍 <b>Top Countries:</b>"
    )

    inline_kb = []
    for idx, (code, name, emoji_id) in enumerate(sorted_countries[:15], 1):
        percentage = "100.0%" if idx == 1 else "0.0%"
        btn_text = f"{idx}. {name} — {percentage}"
        
        btn = {
            "text": btn_text,
            "callback_data": f"traffic_click_{code}",
            "style": "primary",
            "icon_custom_emoji_id": emoji_id
        }
        inline_kb.append([btn])

    inline_kb.append([
        {"text": "Refresh", "callback_data": "refresh_traffic", "style": "success", "icon_custom_emoji_id": "5017470156276761427"}
    ])

    if is_edit:
        try:
            await message_obj.edit_text(text=traffic_header, reply_markup=json.dumps({"inline_keyboard": inline_kb}), parse_mode="HTML")
        except Exception:
            pass
    else:
        await message_obj.reply_text(text=traffic_header, reply_markup=json.dumps({"inline_keyboard": inline_kb}), parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SERVICES, COUNTRY_PRICES, INBOX_NUMBERS, USER_PREFIXES, USER_NUMBER_INDICES, ADMIN_UIDS, USER_DATABASE
    if not update.message:
        return
        
    user_id = update.effective_user.id
    u_data = get_user_data(user_id)
    state = context.user_data.get("state")

    if text := update.message.text:
        text = text.strip()
    else:
        text = ""

    if user_id in ADMIN_UIDS and state == "WAITING_BROADCAST_MSG":
        context.user_data["state"] = None
        broadcast_count = 0
        failed_count = 0
        
        for uid in list(USER_DATABASE.keys()):
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
                broadcast_count += 1
            except Exception:
                failed_count += 1

        await update.message.reply_text(
            f"📢 <b>Broadcast Completed!</b>\n\n"
            f"✅ Successfully sent: <b>{broadcast_count}</b> users\n"
            f"❌ Failed: <b>{failed_count}</b> users",
            parse_mode="HTML"
        )
        return

    if user_id == ROOT_ADMIN_UID and state == "WAITING_NEW_ADMIN_ID":
        context.user_data["state"] = None
        try:
            new_admin_id = int(text)
            ADMIN_UIDS.add(new_admin_id)
            await update.message.reply_text(f"✅ Success! User ID <code>{new_admin_id}</code> is now an Admin.", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID!")
        return

    if user_id == ROOT_ADMIN_UID and state == "WAITING_REMOVE_ADMIN_ID":
        context.user_data["state"] = None
        try:
            rem_admin_id = int(text)
            if rem_admin_id == ROOT_ADMIN_UID:
                await update.message.reply_text("❌ You cannot remove the Root Admin!")
            elif rem_admin_id in ADMIN_UIDS:
                ADMIN_UIDS.remove(rem_admin_id)
                await update.message.reply_text(f"✅ Success! User ID <code>{rem_admin_id}</code> has been removed from Admins.", parse_mode="HTML")
            else:
                await update.message.reply_text("❌ This User ID is not in the Admin list.")
        except ValueError:
            await update.message.reply_text("❌ Invalid User ID!")
        return

    if text == "Live Traffic":
        await send_live_traffic(update.message, is_edit=False)
        return

    if state == "WAITING_SEARCH_QUERY":
        if text:
            search_query = text
            context.user_data["state"] = None
            
            matching_numbers = []
            for (srv, cnt), nums in INBOX_NUMBERS.items():
                for n in nums:
                    if search_query in n:
                        formatted_n = f"+{n}" if not n.startswith("+") else n
                        matching_numbers.append((srv, cnt, formatted_n))

            if not matching_numbers:
                await update.message.reply_text(f"⚠️ <b>No numbers found matching query:</b> <code>{search_query}</code>", parse_mode="HTML")
                return

            msg_header = f"🔍 <b>Search Results for:</b> <code>{search_query}</code>\n"
            inline_kb = []
            for srv, cnt, num in matching_numbers[:10]:
                c_info = RAW_FLAG_EMOJIS.get(cnt, {"name": cnt, "id": "5911143844304393105"})
                btn = {
                    "text": f"[{srv}] {num}",
                    "copy_text": {"text": num},
                    "style": "primary",
                    "icon_custom_emoji_id": c_info.get("id", "5911143844304393105")
                }
                inline_kb.append([btn])

            await update.message.reply_text(text=msg_header, reply_markup=json.dumps({"inline_keyboard": inline_kb}), parse_mode="HTML")
            return

    if state == "WAITING_PREFIX_INPUT":
        if text:
            prefix_val = text
            srv_name = context.user_data.get("current_service")
            c_code = context.user_data.get("current_country")
            
            all_nums = INBOX_NUMBERS.get((srv_name, c_code), [])
            matching_nums = [n for n in all_nums if prefix_val in n]

            if not matching_nums:
                if (user_id, srv_name, c_code) in USER_PREFIXES:
                    del USER_PREFIXES[(user_id, srv_name, c_code)]
                context.user_data["state"] = None
                await update.message.reply_text(
                    f"⚠️ <b>No numbers found for prefix:</b> <code>{prefix_val}</code>.\nPrefix has been automatically removed. You can try setting another prefix.",
                    parse_mode="HTML"
                )
                await show_country_numbers(update.message, user_id, srv_name, c_code, is_edit=False, is_change=False)
                return

            USER_PREFIXES[(user_id, srv_name, c_code)] = prefix_val
            USER_NUMBER_INDICES[(user_id, srv_name, c_code)] = 0
            context.user_data["state"] = None
            await update.message.reply_text(f"✅ Prefix successfully set to: <code>{prefix_val}</code>", parse_mode="HTML")
            
            await show_country_numbers(update.message, user_id, srv_name, c_code, is_edit=False, is_change=False)
            return

    if user_id in ADMIN_UIDS and state == "WAITING_NUMBER_FILE":
        if update.message.document:
            file = await update.message.document.get_file()
            file_bytes = await file.download_as_bytearray()
            file_content = file_bytes.decode("utf-8", errors="ignore")
            
            lines = [line.strip() for line in file_content.splitlines() if line.strip()]
            srv_name = context.user_data.get("upload_srv")
            c_code = context.user_data.get("upload_cnt")

            key = (srv_name, c_code)
            if key not in INBOX_NUMBERS:
                INBOX_NUMBERS[key] = []
            INBOX_NUMBERS[key].extend(lines)

            await update.message.reply_text(f"✅ Successfully uploaded <b>{len(lines)}</b> numbers for <b>{srv_name}</b> ({c_code})!", parse_mode="HTML")
            context.user_data["state"] = None
            return
        else:
            await update.message.reply_text("❌ Please upload a valid .txt file containing numbers.")
            return

    if not text:
        return

    if state == "WAITING_WALLET":
        u_data["wallet"] = text
        context.user_data["state"] = None
        await update.message.reply_text(f"✅ Success! Your Binance UID/Address has been set to: <code>{text}</code>", parse_mode="HTML")
        return

    if user_id in ADMIN_UIDS:
        if state == "WAITING_SERV_NAME":
            service_name = text
            lower_name = service_name.lower()
            matched_id = "5911143844304393105"
            for app_key, info in RAW_APP_EMOJIS.items():
                if app_key in lower_name:
                    matched_id = info["id"]
                    break
            
            SERVICES.append({"name": service_name, "id": matched_id})
            await update.message.reply_text(f"✅ Success! Service **{service_name}** successfully added.", parse_mode="Markdown")
            context.user_data["state"] = None
            return

        elif state == "WAITING_COUNTRY_PRICE":
            try:
                parts = text.rsplit(" ", 1)
                country_input = parts[0].strip().upper()
                c_price = float(parts[1])
                srv_name = context.user_data.get("target_service")

                matched_code = None
                for code, info in RAW_FLAG_EMOJIS.items():
                    if country_input == code or country_input in info["name"].upper():
                        matched_code = code
                        break

                if matched_code:
                    flag_info = RAW_FLAG_EMOJIS[matched_code]
                    if srv_name not in COUNTRY_PRICES:
                        COUNTRY_PRICES[srv_name] = []
                    
                    COUNTRY_PRICES[srv_name].append({
                        "code": matched_code,
                        "name": flag_info["name"],
                        "phone_code": flag_info["phone_code"],
                        "id": flag_info.get("id", "5911143844304393105"),
                        "price": c_price
                    })
                    await update.message.reply_text(f"✅ Country {flag_info['name']} added to {srv_name} with price ${c_price:.4f}/OTP!")
                else:
                    await update.message.reply_text("❌ Invalid Country!")
            except Exception as e:
                await update.message.reply_text("❌ Maling format!")
            
            context.user_data["state"] = None
            return

    if text == "Withdraw":
        wallet_text = u_data["wallet"]
        wallet_display = (wallet_text[:6] + "••••••••" + wallet_text[-6:]) if (wallet_text != "Not Set" and len(wallet_text) > 10) else wallet_text

        wallet_msg = (
            f"{HTML_EMOJIS['money_bag']} <b>Wallet Center</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{HTML_EMOJIS['user']} User ID: <code>{user_id}</code>\n"
            f"{HTML_EMOJIS['balance']} Balance: ${u_data['balance']:.4f}\n"
            f"{HTML_EMOJIS['paid']} Total Paid: ${u_data['total_paid']:.4f}\n"
            f"{HTML_EMOJIS['referral']} Referrals: {u_data['referrals']}\n"
            f"{HTML_EMOJIS['otp']} OTP Received: {u_data['otp_received']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{HTML_EMOJIS['warn']} Minimum Withdraw: $0.0200\n"
            f"{HTML_EMOJIS['fee']} Network Fee: 0%\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{HTML_EMOJIS['card']} Method: <b>BINANCE</b>\n"
            f"{HTML_EMOJIS['address']} Address: <code>{wallet_display}</code>"
        )

        wallet_kb = {
            "inline_keyboard": [
                [
                    {"text": "Set Wallet", "callback_data": "set_wallet", "style": "primary", "icon_custom_emoji_id": "5776103539872896061"},
                    {"text": "Withdraw", "callback_data": "request_withdraw", "style": "danger", "icon_custom_emoji_id": "5352694861990501856"}
                ]
            ]
        }
        await update.message.reply_text(text=wallet_msg, reply_markup=json.dumps(wallet_kb), parse_mode="HTML")

    elif text == "Get Number":
        if not SERVICES:
            await update.message.reply_text(text="⚠️ Ekhono kono service add kora hoyni.")
            return

        inline_keyboard = []
        row = []
        for service in SERVICES:
            s_name = service["name"]
            s_id = service["id"]
            btn = {
                "text": s_name,
                "callback_data": f"get_srv_{s_name}",
                "style": "primary",
                "icon_custom_emoji_id": s_id
            }
            row.append(btn)
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        if row:
            inline_keyboard.append(row)

        await update.message.reply_text(text="Select a service below:", reply_markup=json.dumps({"inline_keyboard": inline_keyboard}))

    elif text == "Search Number":
        context.user_data["state"] = "WAITING_SEARCH_QUERY"
        await update.message.reply_text(
            text="🔍 <b>Send number prefix to search (e.g. 234809):</b>",
            parse_mode="HTML"
        )

    elif text == "Help":
        help_text = (
            "ℹ️ <b>Help</b>\n\n"
            "• 📥 <b>Get Number</b> — get a new DID\n"
            "• 🔎 <b>Search Number</b> — search fresh numbers by prefix\n"
            "• 📟 <b>Live Traffic</b> — view last 5 minutes SMS traffic\n"
            "• 🔄 <b>Change Number</b> — get the next number from the same country\n"
            "• ✨ <b>Set Prefix</b> — get numbers with a specific prefix\n"
            "• 💸 <b>Withdraw</b> — send a payout request"
        )
        await update.message.reply_text(text=help_text, parse_mode="HTML")

    elif text == "🛠️ Admin Panel" and user_id in ADMIN_UIDS:
        admin_inline_kb = {
            "inline_keyboard": [
                [
                    {"text": "Add Service", "callback_data": "btn_add_service", "style": "success"},
                    {"text": "Del Service", "callback_data": "btn_del_service_start", "style": "danger"}
                ],
                [
                    {"text": "Add Country", "callback_data": "btn_add_country_start", "style": "primary"},
                    {"text": "Del Country", "callback_data": "btn_del_country_start", "style": "danger"}
                ],
                [
                    {"text": "Upload Numbers", "callback_data": "btn_upload_num_start", "style": "success"}
                ],
                [
                    {"text": "Add Admin", "callback_data": "btn_add_admin", "style": "success"},
                    {"text": "Remove Admin", "callback_data": "btn_remove_admin", "style": "danger"}
                ],
                [
                    {"text": "📢 Broadcast", "callback_data": "btn_broadcast_start", "style": "primary"}
                ],
                [
                    {"text": "View Services", "callback_data": "btn_list_services", "style": "primary"}
                ]
            ]
        }
        await update.message.reply_text(text="🛠️ Admin Panel Control Center:", reply_markup=json.dumps(admin_inline_kb))

async def show_country_numbers(message_obj, user_id, srv_name, c_code, is_edit=False, is_change=True):
    global USER_NUMBER_INDICES
    srv_emoji_id = "5911143844304393105"
    for s in SERVICES:
        if s["name"] == srv_name:
            srv_emoji_id = s["id"]
            break

    c_info = RAW_FLAG_EMOJIS.get(c_code, {"name": c_code, "phone_code": "000", "id": "5911143844304393105"})
    all_nums = INBOX_NUMBERS.get((srv_name, c_code), ["2348090240384", "2348090241305", "2348090241791"])

    user_prefix = USER_PREFIXES.get((user_id, srv_name, c_code))
    if user_prefix:
        filtered_nums = [n for n in all_nums if user_prefix in n]
        if not filtered_nums:
            del USER_PREFIXES[(user_id, srv_name, c_code)]
            nums = [f"+{n}" if not n.startswith("+") else n for n in all_nums]
        else:
            nums = [f"+{n}" if not n.startswith("+") else n for n in filtered_nums]
    else:
        nums = [f"+{n}" if not n.startswith("+") else n for n in all_nums]

    if not nums:
        no_num_msg = "⚠️ <b>No numbers available.</b>"
        if is_edit:
            try:
                await message_obj.edit_text(text=no_num_msg, parse_mode="HTML")
            except Exception:
                pass
        else:
            await message_obj.reply_text(text=no_num_msg, parse_mode="HTML")
        return

    key = (user_id, srv_name, c_code)
    current_idx = USER_NUMBER_INDICES.get(key, 0)
    
    if is_change:
        current_idx = (current_idx + 3) % len(nums)
        USER_NUMBER_INDICES[key] = current_idx

    displayed_nums = []
    for i in range(min(3, len(nums))):
        idx = (current_idx + i) % len(nums)
        displayed_nums.append(nums[idx])

    for num in displayed_nums:
        clean_num = num.replace("+", "").strip()
        ACTIVE_NUMBER_ALLOCATIONS[clean_num] = user_id

    msg_header = (
        "🔄 <b>These numbers are activated and ready to receive SMS.</b>\n\n"
        f"<tg-emoji emoji-id='{srv_emoji_id}'>💬</tg-emoji> Service: <b>{srv_name}</b>\n"
        f"<tg-emoji emoji-id='{c_info.get('id', '5911143844304393105')}'>✈️</tg-emoji> Country: {c_info['name']} (+{c_info['phone_code']})"
    )

    inline_kb = []
    for num in displayed_nums:
        btn = {
            "text": f"{num}",
            "copy_text": {"text": num},
            "style": "primary",
            "icon_custom_emoji_id": c_info.get('id', '5911143844304393105')
        }
        inline_kb.append([btn])

    inline_kb.append([
        {"text": "Change Country", "callback_data": f"get_srv_{srv_name}", "style": "primary", "icon_custom_emoji_id": "6327661629412482207"},
        {"text": "Set Prefix", "callback_data": f"open_prefix_{srv_name}_{c_code}", "style": "success", "icon_custom_emoji_id": "5463352748751753567"}
    ])
    inline_kb.append([
        {"text": "Change Number", "callback_data": f"select_country_{srv_name}_{c_code}", "style": "primary", "icon_custom_emoji_id": "5017470156276761427"}
    ])
    inline_kb.append([
        {"text": "OTP Group", "url": "https://t.me/PakistanOTPCommunity", "style": "primary", "icon_custom_emoji_id": "6325738755374194174"}
    ])

    if is_edit:
        try:
            await message_obj.edit_text(text=msg_header, reply_markup=json.dumps({"inline_keyboard": inline_kb}), parse_mode="HTML")
        except Exception:
            pass
    else:
        await message_obj.reply_text(text=msg_header, reply_markup=json.dumps({"inline_keyboard": inline_kb}), parse_mode="HTML")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SERVICES, COUNTRY_PRICES, INBOX_NUMBERS, USER_PREFIXES, USER_NUMBER_INDICES, ADMIN_UIDS
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    u_data = get_user_data(user_id)

    if data == "refresh_traffic":
        await send_live_traffic(query.message, is_edit=True)
        await query.answer(text="Live Traffic Refreshed!", show_alert=False)
        return

    if data == "set_wallet":
        context.user_data["state"] = "WAITING_WALLET"
        await query.message.reply_text("💳 Please send your Binance UID or Wallet Address:")

    elif data == "request_withdraw":
        if u_data["wallet"] == "Not Set":
            await query.message.reply_text("❌ Please set your Binance wallet first using the 'Set Wallet' button.")
            return
        if u_data["balance"] < 0.0200:
            await query.message.reply_text("❌ Insufficient balance! Minimum withdraw is $0.0200.")
            return

        admin_msg = f"🚨 <b>New Withdraw Request!</b>\n\n👤 User ID: <code>{user_id}</code>\n💵 Amount: ${u_data['balance']:.4f}\n💳 Binance: <code>{u_data['wallet']}</code>"
        for adm in ADMIN_UIDS:
            try:
                await context.bot.send_message(chat_id=adm, text=admin_msg, parse_mode="HTML")
            except:
                pass
        await query.message.reply_text("✅ Withdraw request submitted successfully!")

    elif user_id in ADMIN_UIDS and data == "btn_add_service":
        context.user_data["state"] = "WAITING_SERV_NAME"
        await query.message.reply_text(text="📦 Enter new service name:")

    elif user_id in ADMIN_UIDS and data == "btn_del_service_start":
        if not SERVICES:
            await query.message.reply_text("⚠️ No services to delete.")
            return
        kb = [[{"text": f"❌ {s['name']}", "callback_data": f"admin_delsrv_{s['name']}", "style": "danger"}] for s in SERVICES]
        await query.message.reply_text("🗑️ Select service to delete:", reply_markup=json.dumps({"inline_keyboard": kb}))

    elif user_id in ADMIN_UIDS and data.startswith("admin_delsrv_"):
        srv_name = data.replace("admin_delsrv_", "")
        SERVICES = [s for s in SERVICES if s["name"] != srv_name]
        if srv_name in COUNTRY_PRICES:
            del COUNTRY_PRICES[srv_name]
        await query.message.reply_text(f"✅ Service <b>{srv_name}</b> deleted!", parse_mode="HTML")

    elif user_id in ADMIN_UIDS and data == "btn_add_country_start":
        if not SERVICES:
            await query.message.reply_text("⚠️ Add service first.")
            return
        kb = [[{"text": s["name"], "callback_data": f"admin_selsrv_{s['name']}", "style": "primary"}] for s in SERVICES]
        await query.message.reply_text("📦 Select service for country:", reply_markup=json.dumps({"inline_keyboard": kb}))

    elif user_id in ADMIN_UIDS and data.startswith("admin_selsrv_"):
        srv_name = data.replace("admin_selsrv_", "")
        context.user_data["target_service"] = srv_name
        context.user_data["state"] = "WAITING_COUNTRY_PRICE"
        await query.message.reply_text(f"🌍 Send format: <code>[CountryName/Code] [Price]</code>", parse_mode="HTML")

    elif user_id in ADMIN_UIDS and data == "btn_del_country_start":
        if not COUNTRY_PRICES:
            await query.message.reply_text("⚠️ No countries available to delete.")
            return
        kb = []
        for srv, countries in COUNTRY_PRICES.items():
            for c in countries:
                kb.append([{
                    "text": f"❌ {srv} - {c['name']}",
                    "callback_data": f"admin_delcnt_{srv}_{c['code']}",
                    "style": "danger"
                }])
        await query.message.reply_text("🗑️ Select country to delete:", reply_markup=json.dumps({"inline_keyboard": kb}))

    elif user_id in ADMIN_UIDS and data.startswith("admin_delcnt_"):
        parts = data.replace("admin_delcnt_", "").split("_", 1)
        srv_name = parts[0]
        c_code = parts[1]
        if srv_name in COUNTRY_PRICES:
            COUNTRY_PRICES[srv_name] = [c for c in COUNTRY_PRICES[srv_name] if c["code"] != c_code]
        await query.message.reply_text(f"✅ Country code <b>{c_code}</b> removed from <b>{srv_name}</b> successfully!", parse_mode="HTML")

    elif user_id in ADMIN_UIDS and data == "btn_upload_num_start":
        if not SERVICES:
            await query.message.reply_text("⚠️ No service available.")
            return
        kb = [[{"text": s["name"], "callback_data": f"upld_srv_{s['name']}", "style": "success"}] for s in SERVICES]
        await query.message.reply_text("📁 Select service to upload numbers:", reply_markup=json.dumps({"inline_keyboard": kb}))

    elif user_id in ADMIN_UIDS and data.startswith("upld_srv_"):
        srv_name = data.replace("upld_srv_", "")
        countries = COUNTRY_PRICES.get(srv_name, [])
        if not countries:
            await query.message.reply_text(f"⚠️ No countries in <b>{srv_name}</b>.", parse_mode="HTML")
            return
        context.user_data["upload_srv"] = srv_name
        kb = [[{"text": c["name"], "callback_data": f"upld_cnt_{srv_name}_{c['code']}", "style": "primary"}] for c in countries]
        await query.message.reply_text(f"📁 Select country for <b>{srv_name}</b>:", reply_markup=json.dumps({"inline_keyboard": kb}), parse_mode="HTML")

    elif user_id in ADMIN_UIDS and data.startswith("upld_cnt_"):
        parts = data.replace("upld_cnt_", "").split("_", 1)
        context.user_data["upload_srv"] = parts[0]
        context.user_data["upload_cnt"] = parts[1]
        context.user_data["state"] = "WAITING_NUMBER_FILE"
        await query.message.reply_text(f"📁 Now upload the <b>.txt file</b> for numbers.", parse_mode="HTML")

    elif user_id == ROOT_ADMIN_UID and data == "btn_add_admin":
        context.user_data["state"] = "WAITING_NEW_ADMIN_ID"
        await query.message.reply_text("➕ Please send the Telegram User ID of the new Admin:")

    elif user_id == ROOT_ADMIN_UID and data == "btn_remove_admin":
        context.user_data["state"] = "WAITING_REMOVE_ADMIN_ID"
        admin_list_str = ", ".join([str(uid) for uid in ADMIN_UIDS if uid != ROOT_ADMIN_UID]) or "None"
        await query.message.reply_text(f"❌ Current Admins: {admin_list_str}\n\nPlease send the Telegram User ID to remove from Admins:")

    elif user_id in ADMIN_UIDS and data == "btn_broadcast_start":
        context.user_data["state"] = "WAITING_BROADCAST_MSG"
        await query.message.reply_text(
            "📢 <tg-emoji emoji-id='5334590977837403844'>📤</tg-emoji> <b>Send the broadcast message, photo, or video now:</b>",
            parse_mode="HTML"
        )

    elif data.startswith("get_srv_"):
        srv_name = data.replace("get_srv_", "")
        countries = COUNTRY_PRICES.get(srv_name, [])
        if not countries:
            await query.message.reply_text(text=f"⚠️ No countries found for <b>{srv_name}</b>.", parse_mode="HTML")
            return

        inline_kb = []
        for idx, c in enumerate(countries):
            btn_text = f"{c['name']} (+{c['phone_code']}) | ${c['price']:.4f}/OTP"
            btn_style = "success" if idx % 2 == 0 else "primary"
            btn = {
                "text": btn_text,
                "callback_data": f"select_country_{srv_name}_{c['code']}",
                "style": btn_style,
                "icon_custom_emoji_id": c.get("id", "5911143844304393105")
            }
            inline_kb.append([btn])
        inline_kb.append([{"text": "Back To Services", "callback_data": "back_to_services", "style": "success"}])

        try:
            await query.message.edit_text(text="Available countries:", reply_markup=json.dumps({"inline_keyboard": inline_kb}))
        except Exception:
            pass

    elif data.startswith("select_country_"):
        parts = data.replace("select_country_", "").split("_", 1)
        srv_name = parts[0]
        c_code = parts[1]
        await show_country_numbers(query.message, user_id, srv_name, c_code, is_edit=True, is_change=True)

    elif data.startswith("open_prefix_"):
        parts = data.replace("open_prefix_", "").split("_", 1)
        srv_name = parts[0]
        c_code = parts[1]
        
        current_p = USER_PREFIXES.get((user_id, srv_name, c_code))

        if not current_p:
            context.user_data["state"] = "WAITING_PREFIX_INPUT"
            context.user_data["current_service"] = srv_name
            context.user_data["current_country"] = c_code
            await query.message.reply_text(
                text="✏️ <b>Send prefix (5/6/7 digits).</b>\nExample: <code>15501</code> or <code>2376205</code>",
                parse_mode="HTML"
            )
        else:
            prefix_msg = f"✅ <b>Prefix already set:</b> <code>{current_p}</code>\nChoose:"
            prefix_kb = {
                "inline_keyboard": [
                    [
                        {"text": "Change Prefix", "callback_data": f"chg_prefix_{srv_name}_{c_code}", "style": "primary"},
                        {"text": "Clear Prefix", "callback_data": f"clr_prefix_{srv_name}_{c_code}", "style": "danger"}
                    ],
                    [
                        {"text": "Cancel", "callback_data": f"select_country_{srv_name}_{c_code}", "style": "primary"}
                    ]
                ]
            }
            try:
                await query.message.edit_text(text=prefix_msg, reply_markup=json.dumps(prefix_kb), parse_mode="HTML")
            except Exception:
                pass

    elif data.startswith("chg_prefix_"):
        parts = data.replace("chg_prefix_", "").split("_", 1)
        context.user_data["state"] = "WAITING_PREFIX_INPUT"
        context.user_data["current_service"] = parts[0]
        context.user_data["current_country"] = parts[1]
        await query.message.reply_text(
            text="✏️ <b>Send new prefix (5/6/7 digits):</b>",
            parse_mode="HTML"
        )

    elif data.startswith("clr_prefix_"):
        parts = data.replace("clr_prefix_", "").split("_", 1)
        srv_name = parts[0]
        c_code = parts[1]
        
        if (user_id, srv_name, c_code) in USER_PREFIXES:
            del USER_PREFIXES[(user_id, srv_name, c_code)]
        if (user_id, srv_name, c_code) in USER_NUMBER_INDICES:
            del USER_NUMBER_INDICES[(user_id, srv_name, c_code)]
        
        await query.answer(text="Prefix cleared successfully!", show_alert=True)
        await show_country_numbers(query.message, user_id, srv_name, c_code, is_edit=True, is_change=False)

    elif data == "back_to_services":
        if not SERVICES:
            await query.message.edit_text(text="⚠️ No services available.")
            return

        inline_keyboard = []
        row = []
        for service in SERVICES:
            s_name = service["name"]
            s_id = service["id"]
            btn = {
                "text": s_name,
                "callback_data": f"get_srv_{s_name}",
                "style": "primary",
                "icon_custom_emoji_id": s_id
            }
            row.append(btn)
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        if row:
            inline_keyboard.append(row)

        try:
            await query.message.edit_text(text="Select a service below:", reply_markup=json.dumps({"inline_keyboard": inline_keyboard}))
        except Exception:
            pass

def detect_service_country_and_language(full_msg, number):
    service_name = "SMS"
    service_id = "5911143844304393105"
    
    lower_msg = full_msg.lower()
    for srv_key, info in RAW_APP_EMOJIS.items():
        if srv_key in lower_msg:
            service_name = srv_key.capitalize()
            service_id = info["id"]
            break

    # Robust country detection based strictly on number prefix (longest match first)
    clean_num = number.replace("+", "").strip()
    country_code = "US"
    country_info = RAW_FLAG_EMOJIS["US"]
    
    sorted_countries = sorted(RAW_FLAG_EMOJIS.items(), key=lambda x: len(x[1]["phone_code"]), reverse=True)
    for code, info in sorted_countries:
        p_code = info["phone_code"]
        if p_code != "?" and clean_num.startswith(p_code):
            country_code = code
            country_info = info
            break

    prefix_val = clean_num[:6] if len(clean_num) >= 6 else clean_num

    lang_name = "English"
    if any(c in full_msg for c in "ěščřžýáíéúůťďňĚŠČŘŽÝÁÍÉÚŮŤĎŇ"):
        lang_name = "Czech"
    elif any(c in full_msg for c in "àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ"):
        lang_name = "French"
    elif any(c in full_msg for c in "äöüßÄÖÜ"):
        lang_name = "German"
    elif any(c in full_msg for c in "ñÑáéíóúÁÉÍÓÚ"):
        lang_name = "Spanish"
    elif any(c in full_msg for c in "абвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"):
        lang_name = "Russian"

    return service_name, service_id, country_code, country_info, prefix_val, lang_name

async def webhook_handler(request):
    try:
        if request.can_read_body:
            data = await request.json()
        else:
            data = {}
    except Exception:
        data = {}

    params = dict(request.query)
    params.update(data)

    number = params.get("number") or params.get("called_number", "")
    number = number.strip().replace("+", "")
    if "{{" in number or "}}" in number or not number:
        number = "22898880555"

    full_msg = params.get("full_msg") or params.get("smstext", "N/A")
    if "{{" in full_msg or "}}" in full_msg or not full_msg:
        full_msg = "[TikTok] 236368 je váš ověřovací kód"

    otp_match = re.search(r'\b\d{3}[- ]?\d{3}\b|\b\d{4,6}\b', full_msg)
    otp_code = otp_match.group(0) if otp_match else "N/A"

    service_name, srv_emoji_id, country_code, c_info, prefix_val, lang_name = detect_service_country_and_language(full_msg, number)

    bot_app = request.app['bot_application']

    target_user_id = ACTIVE_NUMBER_ALLOCATIONS.get(number)
    if target_user_id:
        user_msg = (
            "📧 <tg-emoji emoji-id='5431551436502611633'>📬</tg-emoji> <b>New DID Received!</b>\n"
            f"Number: <code>+{number}</code>\n"
            f"Service: <tg-emoji emoji-id='{srv_emoji_id}'>💬</tg-emoji> {service_name}\n"
            f"OTP: <code>{otp_code}</code>\n"
            f"Status: Paid: 0.000000"
        )
        user_kb = {
            "inline_keyboard": [
                [
                    {"text": "Full Msg", "copy_text": {"text": full_msg}, "style": "primary", "icon_custom_emoji_id": "5348469219761626211"}
                ]
            ]
        }
        try:
            await bot_app.bot.send_message(
                chat_id=target_user_id,
                text=user_msg,
                reply_markup=json.dumps(user_kb),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to send webhook message: {e}")

    group_msg = (
        f"Container\n"
        f"<tg-emoji emoji-id='{c_info['id']}'>🌐</tg-emoji> #{country_code} <tg-emoji emoji-id='{srv_emoji_id}'>💬</tg-emoji> {number} #{lang_name}\n"
        f"➡️ Prefix: {prefix_val}"
    )
    group_kb = {
        "inline_keyboard": [
            [
                {
                    "text": f"{otp_code}", 
                    "copy_text": {"text": otp_code}, 
                    "style": "primary", 
                    "icon_custom_emoji_id": "5411184095994601436"
                },
                {
                    "text": "Full Msg", 
                    "copy_text": {"text": full_msg}, 
                    "style": "primary", 
                    "icon_custom_emoji_id": "6064179391691235813"
                }
            ],
            [
                {
                    "text": "🤖 ATC Bot", 
                    "url": "https://t.me/urbannumber_bot", 
                    "style": "success", 
                    "icon_custom_emoji_id": srv_emoji_id
                }
            ]
        ]
    }
    try:
        await bot_app.bot.send_message(
            chat_id=OTP_GROUP_CHAT_ID,
            text=group_msg,
            reply_markup=json.dumps(group_kb),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Failed to send group message: {e}")

    return web.Response(text="Postback processed successfully", status=200)

async def run_web_server(application):
    app = web.Application()
    app['bot_application'] = application
    app.router.add_post('/webhook', webhook_handler)
    app.router.add_get('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Webhook server started on port {port}")

if __name__ == '__main__':
    TOKEN = "8806245279:AAEGlCgYM6tUpn9n8XaNEcksnrUkKrYikF8"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", lambda u, c: handle_message(u, c)))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    async def post_init(application):
        asyncio.create_task(run_web_server(application))

    app.post_init = post_init

    app.run_polling()
