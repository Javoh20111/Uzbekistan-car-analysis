import pandas as pd
import numpy as np


def duplicate_remover(df):
    before = len(df)
    print(f"Shape: {df.shape[0]}, {df.shape[1]}. Unique values: {df['url'].nunique()}")
    df = df.drop_duplicates(subset='url', keep='first').copy()
    print(f'Removed elements: {before - len(df)}')

    return df


def model_cleaner(df):
    model_to_name = {
        # LADA (VAZ)
        "2101": "Lada 2101",
        "2102": "Lada 2102",
        "2103": "Lada 2103",
        "2104": "Lada 2104",
        "2105": "Lada 2105",
        "2106": "Lada 2106",
        "2107": "Lada 2107",
        "2108": "Lada Samara 2108",
        "2109": "Lada Samara 2109",
        "21099": "Lada Samara 21099",
        "21011": "Lada 21011",
        "21013": "Lada 21013",
        "21033": "Lada 21033",
        "21060": "Lada 21060",
        "21061": "Lada 21061",
        "21063": "Lada 21063",
        "21071": "Lada 21071",
        "21073": "Lada 21073",
        "21083": "Lada Samara 21083",
        "21093": "Lada Samara 21093",
        "21102": "Lada 21102",
        "21103": "Lada 21103",
        "21106": "Lada 21106",
        "21111": "Lada 21111",
        "21124": "Lada 21124",
        "2121 Нива": "Lada Niva",
        "21214 Niva": "Lada Niva 21214",
        "4x4": "Lada Niva 4x4",
        "Дана": "Lada Niva Dana",
        "Kalina": "Lada Kalina",
        "1117 Kalina универсал": "Lada Kalina Wagon",
        "1118 Kalina седан": "Lada Kalina Sedan",
        "1119 Kalina хэтчбэк": "Lada Kalina Hatchback",
        "2110": "Lada 2110",
        "2111": "Lada 2111",
        "2112": "Lada 2112",
        "2113": "Lada 2113",
        "2114": "Lada 2114",
        "2115": "Lada 2115",

        # GAZ — Volga
        "21": "GAZ 21 Volga",
        "21М": "GAZ 21 Volga",
        "21Р": "GAZ 21 Volga",
        "21УС": "GAZ 21 Volga",
        "22": "GAZ 22 Volga",
        "24": "GAZ 24 Volga",
        "2401": "GAZ 2401",
        "2402": "GAZ 2402",
        "2410": "GAZ 2410 Volga",
        "3102": "GAZ 3102 Volga",
        "3102i": "GAZ 3102i",
        "31013": "GAZ 31013",
        "31029": "GAZ 31029",
        "3110": "GAZ 3110",
        "3111": "GAZ 3111",

        # GAZ — Pobeda
        "M-20": "GAZ Pobeda M-20",
        "20": "GAZ Pobeda",
        "20М": "GAZ Pobeda",

        # GAZ — Chaika / ZIM / M1
        "13 Чайка": "GAZ 13 Chaika",
        "ЗИМ": "GAZ 12 ZIM",
        "12 ЗИМ": "GAZ 12 ZIM",
        "М1": "GAZ M1",

        # GAZ — off-road / trucks
        "69": "GAZ 69",
        "51": "GAZ 51",
        "66": "GAZ 66",
        "67": "GAZ 67",

        # MOSKVICH / IZH
        "400": "Moskvich 400",
        "401": "Moskvich 401",
        "407": "Moskvich 407",
        "410": "Moskvich 410",
        "412": "Moskvich 412",
        "412 Э": "Moskvich 412",
        "2125 Комби": "Moskvich 2125 Kombi",
        "2136 Kombi": "Moskvich 2136 Kombi",
        "2137 Kombi": "Moskvich 2137 Kombi",
        "ASLK 2137": "Moskvich 2137",
        "2140": "Moskvich 2140",
        "ASLK 2140": "Moskvich 2140",
        "2141": "Moskvich 2141",
        "21412": "Moskvich 21412",

        # UAZ
        "469": "UAZ 469",
        "469Б": "UAZ 469",
        "2206": "UAZ 2206",
        "2715": "UAZ 2715",
        "3151": "UAZ 3151",
        "3159": "UAZ 3159",
        "3303": "UAZ 3303",
        "31512-010": "UAZ 31512",
        "31514-012": "UAZ 31514",
        "31519-010": "UAZ 31519",
        "Hunter": "UAZ Hunter",

        # ZAZ
        "965": "ZAZ 965",
        "968": "ZAZ 968",
        "968M": "ZAZ 968M",
        "1102 Таврия": "ZAZ Tavria",
        "1102": "ZAZ Tavria",
        "1111 Ока": "ZAZ Oka",
        "Sens": "ZAZ Sens",

        # DAEWOO (very important in Uzbekistan)
        "Matiz": "Daewoo Matiz",
        "Nexia": "Daewoo Nexia",
        "Damas": "Daewoo Damas",
        "Tico": "Daewoo Tico",
        "Espero": "Daewoo Espero",

        # CHEVROLET (UzAuto)
        "Lacetti": "Chevrolet Lacetti",
        "Gentra": "Chevrolet Gentra",
        "Cobalt": "Chevrolet Cobalt",
        "Spark": "Chevrolet Spark",
        "Malibu": "Chevrolet Malibu",
        "Tracker": "Chevrolet Tracker",
        "Onix": "Chevrolet Onix",
        "Captiva": "Chevrolet Captiva",

        # HYUNDAI
        "Sonata": "Hyundai Sonata",
        "Accent": "Hyundai Accent",
        "Elantra": "Hyundai Elantra",

        # KIA
        "Rio": "Kia Rio",
        "Sportage": "Kia Sportage",

        # VOLKSWAGEN
        "Passat": "Volkswagen Passat",
        "Golf": "Volkswagen Golf",
        "Golf III": "Volkswagen Golf III",
        "Golf VI": "Volkswagen Golf VI",
        "Jetta": "Volkswagen Jetta",
        "Transporter": "Volkswagen Transporter",
        "Scirocco": "Volkswagen Scirocco",

        # NISSAN
        "Maxima": "Nissan Maxima",
        "Skyline GT-R": "Nissan Skyline GT-R",
        "Bluebird": "Nissan Bluebird",
        "R Nessa": "Nissan R'nessa",
        "Pathfinder": "Nissan Pathfinder",

        # TOYOTA
        "Corolla": "Toyota Corolla",
        "Camry": "Toyota Camry",
        "Hiace": "Toyota Hiace",
        "Lite Ace": "Toyota LiteAce",
        "Starlet": "Toyota Starlet",

        # FORD
        "Escort": "Ford Escort",
        "Fiesta": "Ford Fiesta",
        "Scorpio": "Ford Scorpio",
        "Granada": "Ford Granada",
        "Five Hundred": "Ford Five Hundred",

        # MERCEDES-BENZ
        "190": "Mercedes-Benz 190",
        "C 250": "Mercedes-Benz C250",
        "E 230": "Mercedes-Benz E230",
        "SL 320": "Mercedes-Benz SL320",
        "S 550": "Mercedes-Benz S550",

        # BMW
        "520": "BMW 520",

        # HONDA
        "Civic": "Honda Civic",

        # OPEL
        "Vectra": "Opel Vectra",
        "Omega": "Opel Omega",
        "Ascona": "Opel Ascona",
        "Rekord": "Opel Rekord",
        "Admiral": "Opel Admiral",
        "Vivaro": "Opel Vivaro",

        # FIAT
        "Uno": "Fiat Uno",
        "Croma": "Fiat Croma",

        # garbage / unknown
        "Прочее": None,
        "Другая": None,
        "Pickup": None,
        "eT7": None,
        "51": None,   # truck — exclude from car analysis
        "66": None,   # truck
        "67": None,   # military jeep
    }
    brand_map = {
        # Daewoo
        "Tico": "Daewoo",
        "Matiz": "Daewoo",
        "Nexia": "Daewoo",
        "Damas": "Daewoo",
        "Espero": "Daewoo",

        # Chevrolet (UzAuto)
        "Lacetti": "Chevrolet",
        "Spark": "Chevrolet",
        "Cobalt": "Chevrolet",
        "Malibu": "Chevrolet",
        "Tracker": "Chevrolet",
        "Onix": "Chevrolet",
        "Gentra": "Chevrolet",
        "Captiva": "Chevrolet",

        # Volkswagen
        "Passat": "Volkswagen",
        "Golf": "Volkswagen",
        "Golf III": "Volkswagen",
        "Golf VI": "Volkswagen",
        "Jetta": "Volkswagen",
        "Transporter": "Volkswagen",
        "Scirocco": "Volkswagen",

        # Nissan
        "Maxima": "Nissan",
        "Skyline GT-R": "Nissan",
        "Bluebird": "Nissan",
        "R Nessa": "Nissan",
        "Pathfinder": "Nissan",

        # Hyundai
        "Sonata": "Hyundai",
        "Accent": "Hyundai",
        "Elantra": "Hyundai",

        # Kia
        "Rio": "Kia",
        "Sportage": "Kia",

        # Toyota
        "Corolla": "Toyota",
        "Camry": "Toyota",
        "Hiace": "Toyota",
        "Lite Ace": "Toyota",

        # Ford
        "Escort": "Ford",
        "Fiesta": "Ford",
        "Scorpio": "Ford",

        # Mercedes-Benz
        "190": "Mercedes-Benz",
        "C 250": "Mercedes-Benz",
        "SL 320": "Mercedes-Benz",

        # BMW
        "520": "BMW",

        # Opel
        "Vectra": "Opel",
        "Omega": "Opel",
        "Ascona": "Opel",
        "Rekord": "Opel",

        # Fiat
        "Uno": "Fiat",
        "Croma": "Fiat",

        # UAZ
        "469": "UAZ",
        "469Б": "UAZ",
        "3151": "UAZ",
        "3159": "UAZ",
        "3303": "UAZ",
        "2206": "UAZ",

        # ZAZ
        "968": "ZAZ",
        "968M": "ZAZ",
        "1102 Таврия": "ZAZ",
        "1102": "ZAZ",
        "1111 Ока": "ZAZ",

        # Moskvich / IZH
        "412": "Moskvich",
        "412 Э": "Moskvich",
        "2140": "Moskvich",
        "2141": "Moskvich",
        "21412": "Moskvich",
        "ASLK 2140": "Moskvich",
        "ASLK 2137": "Moskvich",
        "2137 Kombi": "Moskvich",
        "2136 Kombi": "Moskvich",

        # GAZ
        "24": "GAZ",
        "2410": "GAZ",
        "2401": "GAZ",
        "2402": "GAZ",
        "3102": "GAZ",
        "31029": "GAZ",
        "3110": "GAZ",
        "3102i": "GAZ",

        # Lada (VAZ)
        "2101": "Lada",
        "2102": "Lada",
        "2103": "Lada",
        "2104": "Lada",
        "2105": "Lada",
        "2106": "Lada",
        "2107": "Lada",
        "2108": "Lada",
        "2109": "Lada",
        "21011": "Lada",
        "21013": "Lada",
        "21051": "Lada",
        "21061": "Lada",
        "21071": "Lada",
        "21073": "Lada",
        "21083": "Lada",
        "21093": "Lada",
        "21099": "Lada",

        "2110": "Lada",
        "2111": "Lada",
        "2113": "Lada",
        "21106": "Lada",
        "21124": "Lada",

        "2121 Нива": "Lada",
        "21214 Niva": "Lada",
        "4x4": "Lada",

        "1117 Kalina универсал": "Lada",
        "1118 Kalina седан": "Lada",
        "1119 Kalina хэтчбэк": "Lada",

        # fallback garbage
        "Прочее": None,
        "Другая": None,
    }

    df['model_clean'] = df['model'].str.replace(":","", regex=False).str.strip()
    print('Removed ":"')
    df['car_name'] = df['model_clean'].map(model_to_name)

    def assign_brand(model):
        if model.isdigit():
            num = int(model)

            if 2100 <= num <= 2199:
                return 'Lada'
            
            elif num in [24, 31, 3102, 31029, 3110]:
                return 'GAZ'
            
            elif num in [80, 100, 200, 50]:
                return 'Audi'
            
            elif num in [2140, 2141, 412]:
                return 'Moskvich'
        return None

    def get_brand(model):
        model = str(model)
        brand = assign_brand(model)

        if brand:
            return brand

        for key in brand_map:
            if key.lower()in model.lower():
                return brand_map[key]
        return "Other"
    
    df["brand"] = df["model_clean"].apply(get_brand)
    df["car_name"] = df["car_name"].fillna(df["model_clean"])
    df = df.rename(columns={"model":"model_raw"})

    print(df[['model_clean', 'car_name']].head())


    return df


def price_validatetor(df):
    df['currency'] = df['currency'].fillna('USD')
    exchange_rate = 12000

    df['price'] = pd.to_numeric(df['price'].astype(str).str.replace(r'[^\d]', '', regex=True),
        errors='coerce'
    )

    df['price_usd'] = df['price']
    df.loc[df['currency'] == 'UZS', 'price_usd'] = (
        df.loc[df['currency'] == 'UZS', 'price_usd'] / exchange_rate
    ).round(1)

    df = df.rename(columns={"price":"price_raw"})

    # Using statistical measurements
    Q1 = df['price_usd'].quantile(0.25)
    Q3 = df['price_usd'].quantile(0.75)

    IQR = Q3 - Q1
    df["is_outlier"] = (df['price_usd'] < Q1 - 1.5*IQR) | (df['price_usd'] > Q3 + 1.5*IQR)

    print(df.groupby('currency')['currency'].count())
    return df

