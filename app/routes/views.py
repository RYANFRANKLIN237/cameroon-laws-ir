from flask import Blueprint, render_template, send_from_directory, jsonify
import pycountry
from app import pdf_file_map, pdf_storage_path
from src.utils import normalize_filename

views_bp = Blueprint('views', __name__)

# Representative country for languages whose ISO code ≠ a country code
_LANG_COUNTRY_OVERRIDES = {
    "AA": "ET",  # Afar
    "AB": "GE",  # Abkhazian
    "AK": "GH",  # Akan
    "AN": "ES",  # Aragonese
    "AV": "RU",  # Avaric
    "AY": "BO",  # Aymara
    "BA": "RU",  # Bashkir
    "BH": "IN",  # Bihari
    "BI": "VU",  # Bislama
    "BM": "ML",  # Bambara
    "BN": "BD",  # Bengali
    "BO": "CN",  # Tibetan
    "BR": "FR",  # Breton
    "BS": "BA",  # Bosnian
    "CA": "ES",  # Catalan
    "CE": "RU",  # Chechen
    "CH": "GU",  # Chamorro
    "CO": "FR",  # Corsican
    "CR": "CA",  # Cree
    "CS": "CZ",  # Czech
    "CU": "RU",  # Church Slavic
    "CV": "RU",  # Chuvash
    "CY": "GB",  # Welsh
    "DA": "DK",  # Danish
    "DV": "MV",  # Divehi
    "DZ": "BT",  # Dzongkha
    "EE": "GH",  # Ewe
    "EL": "GR",  # Greek
    "EN": "GB",  # English
    "EO": "EU",  # Esperanto (no flag — handled below)
    "EU": "ES",  # Basque
    "FA": "IR",  # Persian
    "FF": "SN",  # Fulah
    "FY": "NL",  # Western Frisian
    "GA": "IE",  # Irish
    "GD": "GB",  # Scottish Gaelic
    "GL": "ES",  # Galician
    "GN": "PY",  # Guarani
    "GU": "IN",  # Gujarati
    "GV": "GB",  # Manx
    "HA": "NG",  # Hausa
    "HE": "IL",  # Hebrew
    "HI": "IN",  # Hindi
    "HO": "PG",  # Hiri Motu
    "HY": "AM",  # Armenian
    "HZ": "NA",  # Herero
    "IA": "EU",  # Interlingua
    "ID": "ID",  # Indonesian
    "IE": "EU",  # Interlingue
    "IG": "NG",  # Igbo
    "II": "CN",  # Sichuan Yi
    "IK": "US",  # Inupiaq
    "IO": "EU",  # Ido
    "IU": "CA",  # Inuktitut
    "JA": "JP",  # Japanese
    "JV": "ID",  # Javanese
    "KA": "GE",  # Georgian
    "KG": "CG",  # Kongo
    "KI": "KE",  # Kikuyu
    "KJ": "NA",  # Kuanyama
    "KK": "KZ",  # Kazakh
    "KL": "GL",  # Kalaallisut
    "KM": "KH",  # Khmer
    "KN": "IN",  # Kannada
    "KO": "KR",  # Korean
    "KR": "NG",  # Kanuri
    "KS": "IN",  # Kashmiri
    "KU": "IQ",  # Kurdish
    "KV": "RU",  # Komi
    "KW": "GB",  # Cornish
    "KY": "KG",  # Kirghiz
    "LA": "VA",  # Latin
    "LB": "LU",  # Luxembourgish
    "LG": "UG",  # Ganda
    "LI": "NL",  # Limburgan
    "LN": "CD",  # Lingala
    "LO": "LA",  # Lao
    "LT": "LT",  # Lithuanian
    "LU": "CD",  # Luba-Katanga
    "LV": "LV",  # Latvian
    "MG": "MG",  # Malagasy
    "MH": "MH",  # Marshallese
    "MI": "NZ",  # Maori
    "MK": "MK",  # Macedonian
    "ML": "IN",  # Malayalam
    "MN": "MN",  # Mongolian
    "MR": "IN",  # Marathi
    "MS": "MY",  # Malay
    "MT": "MT",  # Maltese
    "MY": "MM",  # Burmese
    "NA": "NR",  # Nauru
    "NB": "NO",  # Norwegian Bokmål
    "ND": "ZW",  # North Ndebele
    "NE": "NP",  # Nepali
    "NG": "NA",  # Ndonga
    "NN": "NO",  # Norwegian Nynorsk
    "NO": "NO",  # Norwegian
    "NR": "ZA",  # South Ndebele
    "NV": "US",  # Navajo
    "NY": "MW",  # Chichewa
    "OC": "FR",  # Occitan
    "OJ": "CA",  # Ojibwa
    "OM": "ET",  # Oromo
    "OR": "IN",  # Oriya
    "OS": "GE",  # Ossetian
    "PA": "IN",  # Punjabi
    "PI": "IN",  # Pali
    "PS": "AF",  # Pashto
    "QU": "PE",  # Quechua
    "RM": "CH",  # Romansh
    "RN": "BI",  # Rundi
    "RO": "RO",  # Romanian
    "RU": "RU",  # Russian
    "RW": "RW",  # Kinyarwanda
    "SA": "IN",  # Sanskrit
    "SC": "IT",  # Sardinian
    "SD": "PK",  # Sindhi
    "SE": "NO",  # Northern Sami
    "SG": "CF",  # Sango
    "SI": "LK",  # Sinhala
    "SK": "SK",  # Slovak
    "SL": "SI",  # Slovenian
    "SM": "WS",  # Samoan
    "SN": "ZW",  # Shona
    "SO": "SO",  # Somali
    "SQ": "AL",  # Albanian
    "SR": "RS",  # Serbian
    "SS": "SZ",  # Swati
    "ST": "LS",  # Southern Sotho
    "SU": "ID",  # Sundanese
    "SV": "SE",  # Swedish
    "SW": "KE",  # Swahili
    "TA": "IN",  # Tamil
    "TE": "IN",  # Telugu
    "TG": "TJ",  # Tajik
    "TH": "TH",  # Thai
    "TI": "ER",  # Tigrinya
    "TK": "TM",  # Turkmen
    "TL": "PH",  # Tagalog
    "TN": "BW",  # Tswana
    "TO": "TO",  # Tonga
    "TR": "TR",  # Turkish
    "TS": "ZA",  # Tsonga
    "TT": "RU",  # Tatar
    "TW": "GH",  # Twi
    "TY": "PF",  # Tahitian
    "UG": "CN",  # Uighur
    "UK": "UA",  # Ukrainian
    "UR": "PK",  # Urdu
    "UZ": "UZ",  # Uzbek
    "VE": "ZA",  # Venda
    "VI": "VN",  # Vietnamese
    "VO": "EU",  # Volapük
    "WA": "BE",  # Walloon
    "WO": "SN",  # Wolof
    "XH": "ZA",  # Xhosa
    "YI": "IL",  # Yiddish
    "YO": "NG",  # Yoruba
    "ZA": "CN",  # Zhuang
    "ZH": "CN",  # Chinese
    "ZU": "ZA",  # Zulu
}


def _country_to_flag(country_code: str) -> str:
    """Convert ISO 3166-1 alpha-2 to a flag emoji (regional indicators)."""
    if not country_code or len(country_code) != 2 or country_code == "EU":
        return "🌐"
    return "".join(chr(ord(c) + 127397) for c in country_code.upper())


def _country_for_language(lang_code: str) -> str | None:
    """Return a representative ISO country code for flag images, or None."""
    code = lang_code.upper()
    country = _LANG_COUNTRY_OVERRIDES.get(code)
    if not country:
        if pycountry.countries.get(alpha_2=code):
            country = code
        else:
            return None
    if country == "EU":
        return None
    return country


def _flag_for_language(lang_code: str) -> str:
    country = _country_for_language(lang_code)
    if not country:
        return "🌐"
    return _country_to_flag(country)


def _get_languages():
    """Return ISO 639-1 languages from pycountry, sorted by name, with flags."""
    languages = []
    for lang in pycountry.languages:
        if not hasattr(lang, "alpha_2"):
            continue
        code = lang.alpha_2.upper()
        country = _country_for_language(code)
        languages.append({
            "code": code,
            "name": lang.name,
            "flag": _flag_for_language(code),
            "country": country,
        })
    languages.sort(key=lambda item: item["name"].lower())
    return languages


@views_bp.route('/')
def onboarding():
    return render_template('onboarding.html')

@views_bp.route('/search')
def search_home():
    return render_template('search.html', languages=_get_languages())

@views_bp.route('/metrics')
def metrics():
    return render_template('metrics.html')

@views_bp.route('/view-pdf/<path:source_name>')
def serve_legal_pdf(source_name):
    norm_request = normalize_filename(source_name)
    actual_filename = pdf_file_map.get(norm_request)
    if actual_filename:
        return send_from_directory(pdf_storage_path, actual_filename)
    return jsonify({
        "error": "PDF not found",
        "details": f"Could not match '{source_name}' to any file in storage."
    }), 404


@views_bp.route('/viewer')
def pdf_viewer():
    """PDF.js viewer: ?source=&page=&q= for page jump + text highlight."""
    return render_template('viewer.html')
