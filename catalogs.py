"""
System katalogów produktowych.

Obsługuje różne katalogi (zlewy, LED, etc.) z osobnymi kategoriami,
kolorami, danymi SEO i mapowaniem BaseLinker category_id.
"""

CATALOGS = {
    "granitowe_zlewy": {
        "name": "Granitowe Zlewy",
        "categories": [
            "Zestaw (zlew + bateria + syfon)",
            "Zestaw (zlew + bateria)",
            "Zestaw (zlew + bateria + dozownik + syfon)",
            "Zlew granitowy",
            "Bateria kuchenna",
            "Syfon",
            "Dozownik płynu",
            "Akcesoria (wężyk / ruszt / kratka)",
        ],
        "kolor_map": {
            "Czarno-złoty": {"accent": "black-gold", "metal": "gold", "sink": "black granite"},
            "Czarny mat": {"accent": "matte black", "metal": "matte black", "sink": "black granite"},
            "Chrom / Srebro": {"accent": "chrome silver", "metal": "chrome", "sink": "black granite"},
            "Miedziany": {"accent": "copper", "metal": "copper", "sink": "black granite"},
            "Stalowy szczotkowany": {"accent": "brushed steel", "metal": "brushed steel", "sink": "black granite"},
            "Biały": {"accent": "white", "metal": "white", "sink": "white granite"},
            "Szary": {"accent": "grey", "metal": "grey", "sink": "grey granite"},
            "Złoty": {"accent": "gold", "metal": "gold", "sink": "black granite"},
            "Beżowy": {"accent": "beige", "metal": "beige", "sink": "beige granite"},
            "Gun Grey": {"accent": "gun grey", "metal": "gun grey", "sink": "black granite"},
        },
        "kolory_per_element": {
            "kolor_zlew": {
                "Czarny nakrapiany": {"sink": "black speckled granite"},
                "Szary nakrapiany": {"sink": "grey speckled granite"},
                "Biały": {"sink": "white granite"},
                "Beżowy": {"sink": "beige granite", "accent": "beige"},
                "Czarny": {"sink": "solid black granite", "accent": "black"},
                "Szary": {"sink": "solid grey granite", "accent": "grey"},
                "Butelkowa zieleń": {"sink": "bottle green granite", "accent": "green"},
                "Czarny metalik": {"sink": "black metallic granite", "accent": "black metallic"},
                "Czarny onyx kwarc": {"sink": "black onyx quartz granite", "accent": "black onyx"},
                "Pure Black": {"sink": "pure black granite, deep matte black finish", "accent": "pure black"},
                "Black Dotted": {"sink": "black dotted granite with fine dots pattern", "accent": "black dotted"},
                "River Sand": {"sink": "river sand beige granite with warm sandy texture", "accent": "river sand"},
                "Silver Stone": {"sink": "silver stone grey granite with silvery mineral flecks", "accent": "silver stone"},
                "Len (tekstura)": {"sink": "linen textured granite, matte fabric-like surface", "accent": "linen"},
                "Satyna (tekstura)": {"sink": "satin textured granite, smooth semi-matte finish", "accent": "satin"},
                "Miedziany": {"sink": "copper-toned granite", "accent": "copper"},
            },
            "kolor_bateria": {
                "Czarno-złota": {"accent": "black body with gold handle and gold accents", "metal": "gold"},
                "Czarny mat": {"accent": "fully matte black finish with no reflective surfaces", "metal": "matte black"},
                "Chrom": {"accent": "chrome", "metal": "chrome"},
                "Miedziana": {"accent": "copper", "metal": "copper"},
                "Stalowa szczotkowana": {"accent": "brushed steel", "metal": "brushed steel"},
                "Biała": {"accent": "white", "metal": "white"},
                "Beżowa": {"accent": "beige", "metal": "beige"},
                "Złota": {"accent": "gold", "metal": "gold"},
                "Rose złota": {"accent": "rose gold", "metal": "rose gold"},
                "Szczotkowane złoto": {"accent": "brushed gold", "metal": "brushed gold"},
                "Gun Grey": {"accent": "gun grey", "metal": "gun grey"},
                "Pure Carbon": {"accent": "pure carbon black", "metal": "pure carbon"},
                "Nano PVD złota": {"accent": "nano PVD gold", "metal": "nano PVD gold"},
                "Len": {"accent": "linen texture", "metal": "linen texture"},
                "Satyna": {"accent": "satin texture", "metal": "satin texture"},
                "Granit": {"accent": "granite finish", "metal": "granite"},
                "Granit nakrapiany": {"accent": "speckled granite finish", "metal": "speckled granite"},
                "Szara": {"accent": "grey faucet finish", "metal": "grey"},
                "Stalowa": {"accent": "stainless steel brushed finish", "metal": "stainless steel"},
            },
            "kolor_syfon_widoczny": {
                "Złoty": {"metal": "gold"},
                "Chromowany": {"metal": "chrome"},
                "Czarny mat": {"metal": "matte black"},
                "Beżowy (River Sand)": {"metal": "river sand beige"},
                "Złoty szczotkowany": {"metal": "brushed gold"},
                "Szary": {"metal": "grey"},
            },
            "kolor_dozownik": {
                "Złoty": {"metal": "gold"},
                "Chromowany": {"metal": "chrome"},
                "Czarny mat": {"metal": "matte black"},
                "Beżowy": {"metal": "beige"},
            },
        },
        "seo_data": {
            "zlew": {
                "frazy": [
                    "zlewozmywak granitowy", "zlew granitowy", "zlewozmywak kuchenny granitowy",
                    "zlew granitowy czarny", "zlewozmywak granitowy 1-komorowy",
                    "zlewozmywak granitowy z ociekaczem", "zlewozmywak granitowy nakrapiany",
                ],
                "tytul_przyklady": [
                    "Zlewozmywak granitowy 1-komorowy 80x50 czarny + syfon [52 zn.]",
                    "Zlew granitowy jednokomorowy z ociekaczem czarny 80x50 cm [55 zn.]",
                ],
                "parametry_obowiazkowe": "materiał, kolor, liczba komór, stan, marka, kod producenta",
                "parametry_opcjonalne": "typ montażu, ociekacz, strona ociekacza, wymiary, głębokość komory, średnica odpływu, kształt, min szafka, waga, model",
                "opis_elementy": "wymiary mm, materiał (80% granit), kolor, typ montażu, liczba komór, średnica odpływu, min szafka, waga, co w zestawie, nawiercanie otworów",
                "usp": "Darmowe nawiercanie otworów pod baterię i dozownik. Syfon w zestawie gratis.",
            },
            "bateria": {
                "frazy": [
                    "bateria kuchenna", "bateria zlewozmywakowa", "bateria kuchenna czarna",
                    "bateria kuchenna z wyciagana wylewka", "bateria kuchenna FLEX",
                    "bateria kuchenna czarno-zlota", "bateria kuchenna obrotowa 360",
                ],
                "tytul_przyklady": [
                    "Bateria kuchenna FLEX elastyczna wylewka czarno-zlota 360\u00b0 [57 zn.]",
                    "Bateria zlewozmywakowa stojaca obrotowa czarna z wyciagana [55 zn.]",
                ],
                "parametry_obowiazkowe": "typ montażu, kolor, materiał, stan, marka",
                "parametry_opcjonalne": "typ głowicy, obrót wylewki, rodzaj wylewki, wysokość, zasięg wylewki, przyłącze, wykończenie",
                "opis_elementy": "typ montażu, wysokość, zasięg wylewki, obrót, typ głowicy, przyłącze, kolor, co w zestawie",
                "usp": "Elastyczna wylewka FLEX. Obrót 360 stopni. Ceramiczna głowica.",
            },
            "zestaw": {
                "frazy": [
                    "zestaw zlew granitowy bateria syfon", "zlewozmywak granitowy z bateria",
                    "zestaw zlew granitowy + bateria FLEX + syfon czarny",
                    "zlewozmywak granitowy czarny 1-komorowy z syfonem",
                    "zlew granitowy jednokomorowy z ociekaczem czarny 80x50",
                ],
                "tytul_przyklady": [
                    "Zestaw zlew granitowy + bateria FLEX czarno-zlota + syfon [56 zn.]",
                    "Zlewozmywak kuchenny granitowy jednokomorowy 79x50 + bateria [60 zn.]",
                ],
                "parametry_obowiazkowe": "materiał, kolor, liczba komór, stan, marka, kod producenta",
                "parametry_opcjonalne": "typ montażu, ociekacz, wymiary, głębokość komory, średnica odpływu, min szafka, waga, typ baterii, kolor baterii",
                "opis_elementy": "wymiary zlew mm, materiał granit, kolor, typ montażu, parametry baterii, średnica odpływu, co w zestawie (KOMPLET), nawiercanie",
                "usp": "Wszystko w jednej paczce: zlew + bateria + syfon + montaż. Darmowe nawiercanie otworów. Zero dokupowań.",
            },
            "syfon": {
                "frazy": [
                    "syfon do zlewozmywaka", "syfon kuchenny", "syfon zloty",
                    "syfon do zlewu granitowego", "syfon automatyczny",
                ],
                "tytul_przyklady": [
                    "Syfon do zlewozmywaka granitowego zloty automatyczny 3,5\" [52 zn.]",
                    "Syfon kuchenny do zlewu granitowego chrom z przelewem [53 zn.]",
                ],
                "parametry_obowiazkowe": "kolor, materiał, średnica, stan, marka",
                "parametry_opcjonalne": "typ (automatyczny/manualny), przelew, średnica odpływu, wykończenie",
                "opis_elementy": "średnica, materiał, kolor, typ, kompatybilność z zlewami, co w zestawie",
                "usp": "Dopasowany do zlewów GranitoweZlewy (średnica 3,5\"). Montaż bez narzędzi w 5 minut.",
            },
            "dozownik": {
                "frazy": [
                    "dozownik plynu do zabudowy", "dozownik mydla kuchenny",
                    "dozownik plynu do zlewozmywaka", "dozownik blatowy zloty",
                ],
                "tytul_przyklady": [
                    "Dozownik plynu do zabudowy zloty 300ml blatowy kuchenny [52 zn.]",
                    "Dozownik mydla kuchenny do zlewozmywaka czarny mat 350ml [55 zn.]",
                ],
                "parametry_obowiazkowe": "kolor, materiał, pojemność, stan, marka",
                "parametry_opcjonalne": "typ montażu, średnica otworu, wykończenie, wymiary",
                "opis_elementy": "pojemność ml, materiał, kolor, typ montażu, średnica otworu, kompatybilność",
                "usp": "Montaż w blacie jednym otworem. Pojemny zbiornik 300-350ml.",
            },
            "akcesoria": {
                "frazy": [
                    "wezyk do baterii kuchennej", "ruszt do zlewozmywaka",
                    "kratka do zlewu", "akcesoria do zlewozmywaka granitowego",
                ],
                "tytul_przyklady": [
                    "Wezyk przylaczeniowy do baterii kuchennej 50cm M10 para [48 zn.]",
                    "Ruszt ochronny do zlewozmywaka granitowego 38x28 cm stal [52 zn.]",
                ],
                "parametry_obowiazkowe": "typ, materiał, wymiary, stan, marka",
                "parametry_opcjonalne": "kolor, kompatybilność, długość, średnica",
                "opis_elementy": "typ, wymiary, materiał, kolor, kompatybilność z modelami",
                "usp": "Oryginalne akcesoria GranitoweZlewy. Idealne dopasowanie do naszych zlewów.",
            },
            "other": {
                "frazy": ["wyposażenie kuchni", "akcesoria kuchenne"],
                "tytul_przyklady": ["Produkt kuchenny - opis"],
                "parametry_obowiazkowe": "stan, marka",
                "parametry_opcjonalne": "",
                "opis_elementy": "opis ogólny produktu",
                "usp": "Darmowa wysyłka, gwarancja 24 msc",
            },
        },
        # Jak znaleźć category_id: BaseLinker > Asortym. > Katalogi > [nazwa kategorii]
        # Kliknij kategorię > ID w URL: ...category_id=XXXX
        # Użyj tej wartości jako category_id poniżej.
        # Marcin dostarczy ID z panelu BL. Do tego czasu: 0
        "bl_category_map": {
            "Zestaw (zlew + bateria + syfon)": 0,
            "Zestaw (zlew + bateria)": 0,
            "Zestaw (zlew + bateria + dozownik + syfon)": 0,
            "Zlew granitowy": 0,
            "Bateria kuchenna": 0,
            "Syfon": 0,
            "Dozownik płynu": 0,
            "Akcesoria (wężyk / ruszt / kratka)": 0,
        },
    },
    "led_oswietlenie": {
        "name": "Oświetlenie LED",
        "categories": [
            "Panel LED",
            "Taśma LED",
            "Profil aluminiowy",
            "Zasilacz LED",
            "Sterownik / Ściemniacz",
            "Oprawa LED",
            "Akcesoria LED",
        ],
        "kolor_map": {
            "Biały neutralny": {"accent": "neutral white", "metal": "white", "sink": "white"},
            "Biały ciepły": {"accent": "warm white", "metal": "warm white", "sink": "warm white"},
            "Biały zimny": {"accent": "cool white", "metal": "cool white", "sink": "cool white"},
            "RGB": {"accent": "RGB multicolor", "metal": "RGB", "sink": "RGB"},
            "Czarny": {"accent": "black", "metal": "black", "sink": "black"},
            "Srebrny / Aluminium": {"accent": "silver aluminum", "metal": "aluminum", "sink": "silver"},
        },
        "seo_data": {
            "panel": {
                "frazy": [
                    "panel LED", "panel LED sufitowy", "panel LED 60x60",
                    "oprawa panelowa LED", "panel LED biurowy",
                ],
                "tytul_przyklady": [
                    "Panel LED sufitowy 60x60 40W 4000K biały neutralny [48 zn.]",
                ],
                "parametry_obowiazkowe": "moc W, barwa światła K, wymiary, stan, marka",
                "parametry_opcjonalne": "strumień świetlny lm, żywotność h, IP, CRI, ściemnianie",
                "opis_elementy": "moc, barwa, wymiary, strumień, żywotność, montaż, certyfikaty",
                "usp": "Energooszczędne oświetlenie LED. Gwarancja 3 lata.",
            },
            "tasma": {
                "frazy": [
                    "tasma LED", "tasma LED 12V", "tasma LED RGB",
                    "pasek LED", "tasma LED pod szafki",
                ],
                "tytul_przyklady": [
                    "Taśma LED 12V 5m biała ciepła 60LED/m wodoodporna IP65 [55 zn.]",
                ],
                "parametry_obowiazkowe": "napięcie V, długość m, barwa, IP, stan, marka",
                "parametry_opcjonalne": "liczba LED/m, moc W/m, CRI, ściemnianie, klej 3M",
                "opis_elementy": "napięcie, długość, barwa, IP, moc, montaż, kompatybilność",
                "usp": "Łatwy montaż. Klej 3M w zestawie. Cięcie co 5 cm.",
            },
            "profil": {
                "frazy": [
                    "profil aluminiowy LED", "profil do tasmy LED",
                    "kanal aluminiowy LED", "profil LED wpuszczany",
                ],
                "tytul_przyklady": [
                    "Profil aluminiowy do taśmy LED 2m z kloszem mlecznym [50 zn.]",
                ],
                "parametry_obowiazkowe": "długość m, typ (nakładany/wpuszczany/narożny), materiał, stan, marka",
                "parametry_opcjonalne": "szerokość mm, klosz, zaślepki, uchwyty",
                "opis_elementy": "długość, typ, materiał, klosz, kompatybilność z taśmami",
                "usp": "Estetyczne wykończenie instalacji LED. Klosz mleczny eliminuje punkty świetlne.",
            },
            "zasilacz": {
                "frazy": [
                    "zasilacz LED 12V", "transformator LED",
                    "zasilacz do tasmy LED", "zasilacz LED wodoodporny",
                ],
                "tytul_przyklady": [
                    "Zasilacz LED 12V 60W 5A do taśmy LED IP67 wodoodporny [52 zn.]",
                ],
                "parametry_obowiazkowe": "napięcie wyjściowe V, moc W, IP, stan, marka",
                "parametry_opcjonalne": "prąd A, wymiary, zabezpieczenia, certyfikaty",
                "opis_elementy": "napięcie, moc, prąd, IP, zabezpieczenia, certyfikaty, montaż",
                "usp": "Stabilne napięcie. Zabezpieczenie przed przeciążeniem i zwarciem.",
            },
            "sterownik": {
                "frazy": [
                    "sciemniacz LED", "sterownik LED", "sterownik RGB LED",
                    "dimmer LED 12V", "kontroler tasmy LED",
                ],
                "tytul_przyklady": [
                    "Ściemniacz LED 12-24V z pilotem RF dotykowy panel [48 zn.]",
                ],
                "parametry_obowiazkowe": "napięcie V, max moc W, typ sterowania, stan, marka",
                "parametry_opcjonalne": "pilot, wifi, kompatybilność, kanały",
                "opis_elementy": "napięcie, moc, typ sterowania, kompatybilność, montaż",
                "usp": "Płynna regulacja jasności. Pilot w zestawie.",
            },
            "oprawa": {
                "frazy": [
                    "oprawa LED", "oprawa LED podtynkowa", "oczko LED",
                    "oprawa LED natynkowa", "downlight LED",
                ],
                "tytul_przyklady": [
                    "Oprawa LED podtynkowa okrągła 12W 4000K biała slim [48 zn.]",
                ],
                "parametry_obowiazkowe": "moc W, barwa K, typ montażu, kształt, stan, marka",
                "parametry_opcjonalne": "średnica mm, IP, CRI, ściemnianie, kąt świecenia",
                "opis_elementy": "moc, barwa, typ montażu, średnica, IP, CRI, montaż",
                "usp": "Slim design. Łatwy montaż. Równe światło bez migotania.",
            },
            "akcesoria": {
                "frazy": [
                    "zlaczka do tasmy LED", "konektor LED",
                    "akcesoria do tasmy LED", "lacznik tasmy LED",
                ],
                "tytul_przyklady": [
                    "Złączka do taśmy LED 10mm 2-pin szybkozłączka 5szt [45 zn.]",
                ],
                "parametry_obowiazkowe": "typ, kompatybilność, ilość w opakowaniu, stan, marka",
                "parametry_opcjonalne": "szerokość mm, materiał, IP",
                "opis_elementy": "typ, kompatybilność, materiał, ilość, sposób montażu",
                "usp": "Montaż bez lutowania. Kompatybilne z popularnymi taśmami LED.",
            },
            "other": {
                "frazy": ["oświetlenie LED", "akcesoria oświetleniowe"],
                "tytul_przyklady": ["Produkt oświetleniowy LED - opis"],
                "parametry_obowiazkowe": "stan, marka",
                "parametry_opcjonalne": "",
                "opis_elementy": "opis ogólny produktu",
                "usp": "Energooszczędne oświetlenie LED. Gwarancja 3 lata.",
            },
        },
        # Marcin dostarczy ID z panelu BL. Do tego czasu: 0
        "bl_category_map": {
            "Panel LED": 0,
            "Taśma LED": 0,
            "Profil aluminiowy": 0,
            "Zasilacz LED": 0,
            "Sterownik / Ściemniacz": 0,
            "Oprawa LED": 0,
            "Akcesoria LED": 0,
        },
    },
}


def get_catalog(catalog_name):
    """Zwraca konfigurację katalogu lub None."""
    return CATALOGS.get(catalog_name)


def get_catalog_names():
    """Zwraca listę nazw katalogów (klucze)."""
    return list(CATALOGS.keys())


def get_catalog_display_names():
    """Zwraca dict {klucz: nazwa wyświetlana} dla selectbox."""
    return {k: v["name"] for k, v in CATALOGS.items()}


def get_categories(catalog_name):
    """Zwraca listę kategorii dla katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return []
    return cat["categories"]


def get_kolor_map(catalog_name):
    """Zwraca mapę kolorów dla katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return {}
    return cat["kolor_map"]


def get_seo_key(kategoria):
    """Mapuje kategorię na klucz SEO."""
    kat_lower = kategoria.lower()
    if "zestaw" in kat_lower:
        return "zestaw"
    elif "bateria" in kat_lower:
        return "bateria"
    elif "syfon" in kat_lower:
        return "syfon"
    elif "dozownik" in kat_lower:
        return "dozownik"
    elif "akcesori" in kat_lower:
        return "akcesoria"
    elif "panel" in kat_lower:
        return "panel"
    elif "tasma" in kat_lower or "taśma" in kat_lower:
        return "tasma"
    elif "profil" in kat_lower:
        return "profil"
    elif "zasilacz" in kat_lower:
        return "zasilacz"
    elif "sterownik" in kat_lower or "ściemniacz" in kat_lower:
        return "sterownik"
    elif "oprawa" in kat_lower:
        return "oprawa"
    elif "zlew" in kat_lower:
        return "zlew"
    return "other"


def get_kolory_per_element(catalog_name):
    """Zwraca mapę kolorów per element dla katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return {}
    return cat.get("kolory_per_element", {})


def get_seo_data(catalog_name, kategoria):
    """Zwraca dane SEO dla kategorii w katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return None
    seo_key = get_seo_key(kategoria)
    return cat["seo_data"].get(seo_key)


def get_bl_category_id(catalog_name, kategoria):
    """Zwraca BL category_id dla kategorii. 0 = domyślny BL."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return 0
    return cat["bl_category_map"].get(kategoria, 0)


# ---------------------------------------------------------------------------
# Features per typ produktu (mapowanie parametrów Allegro)
# Źródło: BASELINKER-RECON.md
# ---------------------------------------------------------------------------

# Domyślne pola obecne w każdym produkcie
_DEFAULT_FEATURES = ["Stan", "Stan opakowania", "EAN", "Kod producenta", "Marka"]

FEATURES_PER_TYPE = {
    "zlew": {
        "required": _DEFAULT_FEATURES + [
            "Rodzaj", "Liczba komór", "Materiał wykonania", "Kolor", "Kształt",
            "Dłuższy bok", "Krótszy bok", "Głębokość", "Linia",
            "Zawartość zestawu", "Informacje dodatkowe",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "zestaw": {
        "required": _DEFAULT_FEATURES + [
            "Rodzaj", "Liczba komór", "Materiał wykonania", "Kolor", "Kształt",
            "Dłuższy bok", "Krótszy bok", "Głębokość", "Linia",
            "Zawartość zestawu", "Informacje dodatkowe",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "bateria": {
        "required": _DEFAULT_FEATURES + [
            "Typ montażu", "Typ", "Kolor", "Linia", "Informacje dodatkowe",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "grzalka": {
        "required": _DEFAULT_FEATURES + [
            "Rodzaj", "Moc grzewcza", "Kolor",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "syfon": {
        "required": _DEFAULT_FEATURES + [
            "Kolor", "Materiał wykonania", "Średnica",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "dozownik": {
        "required": _DEFAULT_FEATURES + [
            "Kolor", "Materiał wykonania", "Pojemność",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
    "akcesoria": {
        "required": _DEFAULT_FEATURES + [
            "Typ", "Materiał wykonania", "Wymiary",
        ],
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    },
}


def get_features_for_type(kategoria: str) -> dict:
    """Zwraca mapowanie features (required + defaults) dla kategorii.

    Używa get_seo_key do normalizacji nazwy kategorii.
    """
    seo_key = get_seo_key(kategoria)
    return FEATURES_PER_TYPE.get(seo_key, {
        "required": _DEFAULT_FEATURES,
        "defaults": {"Stan": "Nowy", "Stan opakowania": "oryginalne"},
    })
