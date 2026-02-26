"""
System katalogow produktowych.

Obsluguje rozne katalogi (zlewy, LED, etc.) z osobnymi kategoriami,
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
        },
        "kolory_per_element": {
            "kolor_zlew": {
                "Czarny nakrapiany": {"sink": "black speckled granite"},
                "Szary nakrapiany": {"sink": "grey speckled granite"},
                "Biały": {"sink": "white granite"},
            },
            "kolor_bateria": {
                "Czarno-złota": {"accent": "black-gold", "metal": "gold"},
                "Czarny mat": {"accent": "matte black", "metal": "matte black"},
                "Chrom": {"accent": "chrome", "metal": "chrome"},
                "Miedziana": {"accent": "copper", "metal": "copper"},
                "Stalowa szczotkowana": {"accent": "brushed steel", "metal": "brushed steel"},
            },
            "kolor_syfon_widoczny": {
                "Złoty": {"metal": "gold"},
                "Chromowany": {"metal": "chrome"},
                "Czarny mat": {"metal": "matte black"},
            },
            "kolor_dozownik": {
                "Złoty": {"metal": "gold"},
                "Chromowany": {"metal": "chrome"},
                "Czarny mat": {"metal": "matte black"},
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
                "parametry_obowiazkowe": "material, kolor, liczba komor, stan, marka, kod producenta",
                "parametry_opcjonalne": "typ montazu, ociekacz, strona ociekacza, wymiary, glebokosc komory, srednica odplywu, ksztalt, min szafka, waga, model",
                "opis_elementy": "wymiary mm, material (80% granit), kolor, typ montazu, liczba komor, srednica odplywu, min szafka, waga, co w zestawie, nawiercanie otworow",
                "usp": "Darmowe nawiercanie otworow pod baterie i dozownik. Syfon w zestawie gratis.",
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
                "parametry_obowiazkowe": "typ montazu, kolor, material, stan, marka",
                "parametry_opcjonalne": "typ glowicy, obrot wylewki, rodzaj wylewki, wysokosc, zasieg wylewki, przylacze, wykonczenie",
                "opis_elementy": "typ montazu, wysokosc, zasieg wylewki, obrot, typ glowicy, przylacze, kolor, co w zestawie",
                "usp": "Elastyczna wylewka FLEX. Obrot 360 stopni. Ceramiczna glowica.",
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
                "parametry_obowiazkowe": "material, kolor, liczba komor, stan, marka, kod producenta",
                "parametry_opcjonalne": "typ montazu, ociekacz, wymiary, glebokosc komory, srednica odplywu, min szafka, waga, typ baterii, kolor baterii",
                "opis_elementy": "wymiary zlew mm, material granit, kolor, typ montazu, parametry baterii, srednica odplywu, co w zestawie (KOMPLET), nawiercanie",
                "usp": "Wszystko w jednej paczce: zlew + bateria + syfon + montaz. Darmowe nawiercanie otworow. Zero dokupowan.",
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
                "parametry_obowiazkowe": "kolor, material, srednica, stan, marka",
                "parametry_opcjonalne": "typ (automatyczny/manualny), przelew, srednica odplywu, wykonczenie",
                "opis_elementy": "srednica, material, kolor, typ, kompatybilnosc z zlewami, co w zestawie",
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
                "parametry_obowiazkowe": "kolor, material, pojemnosc, stan, marka",
                "parametry_opcjonalne": "typ montazu, srednica otworu, wykonczenie, wymiary",
                "opis_elementy": "pojemnosc ml, material, kolor, typ montazu, srednica otworu, kompatybilnosc",
                "usp": "Montaz w blacie jednym otworem. Pojemny zbiornik 300-350ml.",
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
                "parametry_obowiazkowe": "typ, material, wymiary, stan, marka",
                "parametry_opcjonalne": "kolor, kompatybilnosc, dlugosc, srednica",
                "opis_elementy": "typ, wymiary, material, kolor, kompatybilnosc z modelami",
                "usp": "Oryginalne akcesoria GranitoweZlewy. Idealne dopasowanie do naszych zlewow.",
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
                "parametry_obowiazkowe": "moc W, barwa swiatla K, wymiary, stan, marka",
                "parametry_opcjonalne": "strumien swietlny lm, zycie h, IP, CRI, sciemnianie",
                "opis_elementy": "moc, barwa, wymiary, strumien, zycie, montaz, certyfikaty",
                "usp": "Energooszczedne oswietlenie LED. Gwarancja 3 lata.",
            },
            "tasma": {
                "frazy": [
                    "tasma LED", "tasma LED 12V", "tasma LED RGB",
                    "pasek LED", "tasma LED pod szafki",
                ],
                "tytul_przyklady": [
                    "Taśma LED 12V 5m biała ciepła 60LED/m wodoodporna IP65 [55 zn.]",
                ],
                "parametry_obowiazkowe": "napiecie V, dlugosc m, barwa, IP, stan, marka",
                "parametry_opcjonalne": "liczba LED/m, moc W/m, CRI, sciemnianie, klej 3M",
                "opis_elementy": "napiecie, dlugosc, barwa, IP, moc, montaz, kompatybilnosc",
                "usp": "Latwy montaz. Klej 3M w zestawie. Cieciu co 5 cm.",
            },
            "profil": {
                "frazy": [
                    "profil aluminiowy LED", "profil do tasmy LED",
                    "kanal aluminiowy LED", "profil LED wpuszczany",
                ],
                "tytul_przyklady": [
                    "Profil aluminiowy do taśmy LED 2m z kloszem mlecznym [50 zn.]",
                ],
                "parametry_obowiazkowe": "dlugosc m, typ (nakladany/wpuszczany/narozny), material, stan, marka",
                "parametry_opcjonalne": "szerokosc mm, klosz, zagluszki, uchwyty",
                "opis_elementy": "dlugosc, typ, material, klosz, kompatybilnosc z tasmami",
                "usp": "Estetyczne wykonczenie instalacji LED. Klosz mleczny eliminuje punkty swietlne.",
            },
            "zasilacz": {
                "frazy": [
                    "zasilacz LED 12V", "transformator LED",
                    "zasilacz do tasmy LED", "zasilacz LED wodoodporny",
                ],
                "tytul_przyklady": [
                    "Zasilacz LED 12V 60W 5A do taśmy LED IP67 wodoodporny [52 zn.]",
                ],
                "parametry_obowiazkowe": "napiecie wyjsciowe V, moc W, IP, stan, marka",
                "parametry_opcjonalne": "prad A, wymiary, zabezpieczenia, certyfikaty",
                "opis_elementy": "napiecie, moc, prad, IP, zabezpieczenia, certyfikaty, montaz",
                "usp": "Stabilne napiecie. Zabezpieczenie przed przeciazeniem i zwarciem.",
            },
            "sterownik": {
                "frazy": [
                    "sciemniacz LED", "sterownik LED", "sterownik RGB LED",
                    "dimmer LED 12V", "kontroler tasmy LED",
                ],
                "tytul_przyklady": [
                    "Ściemniacz LED 12-24V z pilotem RF dotykowy panel [48 zn.]",
                ],
                "parametry_obowiazkowe": "napiecie V, max moc W, typ sterowania, stan, marka",
                "parametry_opcjonalne": "pilot, wifi, kompatybilnosc, kanaly",
                "opis_elementy": "napiecie, moc, typ sterowania, kompatybilnosc, montaz",
                "usp": "Plynna regulacja jasnosci. Pilot w zestawie.",
            },
            "oprawa": {
                "frazy": [
                    "oprawa LED", "oprawa LED podtynkowa", "oczko LED",
                    "oprawa LED natynkowa", "downlight LED",
                ],
                "tytul_przyklady": [
                    "Oprawa LED podtynkowa okrągła 12W 4000K biała slim [48 zn.]",
                ],
                "parametry_obowiazkowe": "moc W, barwa K, typ montazu, ksztalt, stan, marka",
                "parametry_opcjonalne": "srednica mm, IP, CRI, sciemnianie, kat swiecenia",
                "opis_elementy": "moc, barwa, typ montazu, srednica, IP, CRI, montaz",
                "usp": "Slim design. Latwy montaz. Rowne swiatlo bez migotania.",
            },
            "akcesoria": {
                "frazy": [
                    "zlaczka do tasmy LED", "konektor LED",
                    "akcesoria do tasmy LED", "lacznik tasmy LED",
                ],
                "tytul_przyklady": [
                    "Złączka do taśmy LED 10mm 2-pin szybkozłączka 5szt [45 zn.]",
                ],
                "parametry_obowiazkowe": "typ, kompatybilnosc, ilosc w opakowaniu, stan, marka",
                "parametry_opcjonalne": "szerokosc mm, material, IP",
                "opis_elementy": "typ, kompatybilnosc, material, ilosc, sposob montazu",
                "usp": "Montaz bez lutowania. Kompatybilne z popularnymi tasmami LED.",
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
    """Zwraca konfiguracje katalogu lub None."""
    return CATALOGS.get(catalog_name)


def get_catalog_names():
    """Zwraca liste nazw katalogow (klucze)."""
    return list(CATALOGS.keys())


def get_catalog_display_names():
    """Zwraca dict {klucz: nazwa wyswietlana} dla selectbox."""
    return {k: v["name"] for k, v in CATALOGS.items()}


def get_categories(catalog_name):
    """Zwraca liste kategorii dla katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return []
    return cat["categories"]


def get_kolor_map(catalog_name):
    """Zwraca mape kolorow dla katalogu."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return {}
    return cat["kolor_map"]


def get_seo_key(kategoria):
    """Mapuje kategorie na klucz SEO."""
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
    """Zwraca BL category_id dla kategorii. 0 = domyslny BL."""
    cat = CATALOGS.get(catalog_name)
    if not cat:
        return 0
    return cat["bl_category_map"].get(kategoria, 0)
