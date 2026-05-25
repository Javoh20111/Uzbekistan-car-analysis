import pandas as pd
import numpy as np


def duplicate_remover(df):
    before = len(df)
    print(f"Shape: {df.shape[0]}, {df.shape[1]}. Unique values: {df['url'].nunique()}")
    df = df.drop_duplicates(subset='url', keep='first').copy()
    df = df.drop(columns=['posting_date'])
    df = df.drop(columns=['seller_type'])
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

def mileage_cleaner(df):
    df['mileage_raw'] = df['mileage']
    df.loc[df['mileage'] > 500000, 'mileage'] = np.nan

    df.loc[(df['mileage'] < 5000) & (df['price_usd'] < 10000) & (df['year'] < 2023), 'mileage'] = np.nan

    df.loc[(df['mileage'] == 0) &
        (df['year'] < 2024),
        'mileage'
    ] = np.nan

    df['mileage_log'] = np.log1p(df['mileage'])

    df['mileage_group'] = pd.cut(
        df['mileage'],
        bins=[-1, 15000, 50000, 100000, 200000, 500000],
        labels=['new_or_very_low', 'low', 'medium', 'high', 'very_high']
    )

    print(df[['mileage_log','mileage_group', 'mileage']])
    return df

def engine_volume_cleaner(df):
    df['engine_volume_raw'] = df['engine_volume']

    def format_engine_value(x):
        if pd.isna(x):
            return np.nan
        if x >= 1000:
            return x / 1000
        if 100 <= x < 1000:
            return x / 100
        if 10 <= x < 100:
            return x / 10
        if 0 < x < 10:
            return x
        return np.nan
    df['engine_volume_l'] = df['engine_volume_raw'].apply(format_engine_value)

    df.loc[
        (df['engine_volume_l'] < 0.6) | (df['engine_volume_l'] > 6),
        'engine_volume_l'
    ] = np.nan

    df['engine_volume_l'] = df['engine_volume_l'].round(2)


    print(df[['engine_volume_l', 'engine_volume_raw','engine_volume']].describe())
    return df

def owners_count_cleaner(df):

    def format_owners_count(x):
        if pd.isna(x):
            return np.nan
        x = str(x)
        x = x.strip('+')
        return float(x)

    df['owners_count'] = df['owners_count'].apply(format_owners_count)
    df['owners_count'] = df['owners_count'].astype('Int64')
    print(df['owners_count'].describe())
    return df

def seller_type_cleaner(df):
    Translate_list = {
        "Кредит": "Credit",
        "Рассрочка": "Installment plan",
        "Простая продажа": "Direct sale",
        "Возможен обмен": "Exchange possible",
        "Аренда": "Rent",
        "Лизинг": "Leasing"
    }

    def translate(text):
        if pd.isna(text):
            return text
        
        items = [item.strip() for item in text.split(",")]
        translated = [Translate_list.get(item, item) for item in items]
        
        return ", ".join(translated)

    df["sale_type"] = df["sale_type"].apply(translate)
    print(df["sale_type"].value_counts().head(5))
    return df

def year_cleaner(df):
    def devide_eras(x):
        if pd.isna(x):
            return np.nan
        
        if x < 1940:
            return 'pre-1940'
        elif 1940 <= x <= 1949:
            return '1940s'
        elif 1950 <= x <= 1959:
            return '1950s'
        elif 1960 <= x <= 1969:
            return '1960s'
        elif 1970 <= x <= 1979:
            return '1970s'
        elif 1980 <= x <= 1989:
            return '1980s'
        elif 1990 <= x <= 1999:
            return '1990s'
        elif 2000 <= x <= 2009:
            return '2000s'
        elif 2010 <= x <= 2019:
            return '2010s'
        else:
            return '2020s'
    df['era'] = df['year'].apply(devide_eras)
    print(df['era'].value_counts())
    df['car_age'] = 2026 - df['year']
    print(df['car_age'].describe())

    model_min_year = {

    # LADA (VAZ)
    "Lada 2101": 1970,
    "Lada 2102": 1971,
    "Lada 2103": 1972,
    "Lada 2104": 1984,
    "Lada 2105": 1979,
    "Lada 2106": 1976,
    "Lada 2107": 1982,
    "Lada Samara 2108": 1984,
    "Lada Samara 2109": 1987,
    "Lada Samara 21099": 1990,
    "Lada 21011": 1974,
    "Lada 21013": 1977,
    "Lada 21033": 1972,
    "Lada 21060": 1976,
    "Lada 21061": 1976,
    "Lada 21063": 1976,
    "Lada 21071": 1977,
    "Lada 21073": 1977,
    "Lada Samara 21083": 1987,
    "Lada Samara 21093": 1987,
    "Lada 21102": 1996,
    "Lada 21103": 1996,
    "Lada 21106": 2003,
    "Lada 21111": 1998,
    "Lada 21124": 2004,
    "Lada Niva": 1977,
    "Lada Niva 21214": 1994,
    "Lada Niva 4x4": 1977,
    "Lada Niva Dana": 1998,
    "Lada Kalina": 2004,
    "Lada Kalina Wagon": 2006,
    "Lada Kalina Sedan": 2004,
    "Lada Kalina Hatchback": 2004,
    "Lada 2110": 1996,
    "Lada 2111": 1998,
    "Lada 2112": 1999,
    "Lada 2113": 2004,
    "Lada 2114": 2001,
    "Lada 2115": 1997,

    # GAZ — Volga
    "GAZ 21 Volga": 1956,
    "GAZ 22 Volga": 1962,
    "GAZ 24 Volga": 1970,
    "GAZ 2401": 1970,
    "GAZ 2402": 1972,
    "GAZ 2410 Volga": 1985,
    "GAZ 3102 Volga": 1982,
    "GAZ 31013": 1990,
    "GAZ 31029": 1992,
    "GAZ 3110": 1997,
    "GAZ 3111": 2000,
    "GAZ 3102i": 1982,

    # GAZ — Pobeda
    "GAZ Pobeda M-20": 1946,
    "GAZ Pobeda": 1946,

    # GAZ — Chaika / ZIM / M1
    "GAZ 13 Chaika": 1959,
    "GAZ 12 ZIM": 1950,
    "GAZ M1": 1936,

    # GAZ — off-road / trucks
    "GAZ 69": 1952,
    "GAZ 51": 1946,
    "GAZ 66": 1964,
    "GAZ 67": 1943,

    # MOSKVICH
    "Moskvich 400": 1946,
    "Moskvich 401": 1954,
    "Moskvich 407": 1958,
    "Moskvich 410": 1957,
    "Moskvich 412": 1969,
    "Moskvich 2125 Kombi": 1976,
    "Moskvich 2136 Kombi": 1976,
    "Moskvich 2137": 1978,
    "Moskvich 2137 Kombi": 1978,
    "Moskvich 2140": 1976,
    "Moskvich 2141": 1986,
    "Moskvich 21412": 1986,

    # UAZ
    "UAZ 469": 1972,
    "UAZ 2206": 1985,
    "UAZ 2715": 1965,
    "UAZ 3151": 1985,
    "UAZ 3159": 1998,
    "UAZ 3303": 1985,
    "UAZ 31512": 1985,
    "UAZ 31514": 1993,
    "UAZ 31519": 2000,
    "UAZ Hunter": 2003,

    # ZAZ
    "ZAZ 965": 1960,
    "ZAZ 968": 1971,
    "ZAZ 968M": 1979,
    "ZAZ Tavria": 1988,
    "ZAZ Oka": 1988,
    "ZAZ Sens": 2002,

    # DAEWOO
    "Daewoo Matiz": 1998,
    "Daewoo Nexia": 1995,
    "Daewoo Damas": 1991,
    "Daewoo Tico": 1991,
    "Daewoo Espero": 1990,

    # CHEVROLET (UzAuto)
    "Chevrolet Lacetti": 2002,
    "Chevrolet Gentra": 2013,
    "Chevrolet Cobalt": 2011,
    "Chevrolet Spark": 2005,
    "Chevrolet Malibu": 2011,
    "Chevrolet Tracker": 2013,
    "Chevrolet Onix": 2012,
    "Chevrolet Captiva": 2006,

    # HYUNDAI
    "Hyundai Sonata": 1985,
    "Hyundai Accent": 1994,
    "Hyundai Elantra": 1990,

    # KIA
    "Kia Rio": 2000,
    "Kia Sportage": 1993,

    # VOLKSWAGEN
    "Volkswagen Passat": 1973,
    "Volkswagen Golf": 1974,
    "Volkswagen Golf III": 1991,
    "Volkswagen Golf VI": 2008,
    "Volkswagen Jetta": 1979,
    "Volkswagen Transporter": 1950,
    "Volkswagen Scirocco": 1974,

    # NISSAN
    "Nissan Maxima": 1981,
    "Nissan Skyline GT-R": 1969,
    "Nissan Bluebird": 1957,
    "Nissan R'nessa": 1997,
    "Nissan Pathfinder": 1985,

    # TOYOTA
    "Toyota Corolla": 1966,
    "Toyota Camry": 1982,
    "Toyota Hiace": 1967,
    "Toyota LiteAce": 1970,
    "Toyota Starlet": 1973,

    # FORD
    "Ford Escort": 1968,
    "Ford Fiesta": 1976,
    "Ford Scorpio": 1985,
    "Ford Granada": 1972,
    "Ford Five Hundred": 2004,

    # MERCEDES-BENZ
    "Mercedes-Benz 190": 1982,
    "Mercedes-Benz C250": 1993,
    "Mercedes-Benz E230": 1984,
    "Mercedes-Benz SL320": 1989,
    "Mercedes-Benz S550": 2005,

    # BMW
    "BMW 520": 1972,

    # HONDA
    "Honda Civic": 1972,

    # OPEL
    "Opel Vectra": 1988,
    "Opel Omega": 1986,
    "Opel Ascona": 1970,
    "Opel Rekord": 1953,
    "Opel Admiral": 1964,
    "Opel Vivaro": 2001,

    # FIAT
    "Fiat Uno": 1983,
    "Fiat Croma": 1985,
    }

    df["year_valid"] = df.apply(
        lambda row: row["year"] >= model_min_year.get(row["car_name"], 0),
        axis=1
    )
    bad_years = df[~df["year_valid"]][["year", "car_name", "price_usd"]]
    print(bad_years.head(5))
    return df

def district_cleaner(df):
    correction_dict = {
    # TASHKENT CITY - 11 Districts
    "TashkentSergeliyskiy rayon": "Sergeli",
    "Sergeliyskiy rayon": "Sergeli",
    "ТашкентСергелийский район": "Sergeli",
    "Sergeli": "Sergeli",
    
    "TashkentYunusabadskiy rayon": "Yunusabad",
    "Yunusabadskiy rayon": "Yunusabad",
    "ТашкентЮнусабадский район": "Yunusabad",
    "Yunusabad": "Yunusabad",
    
    "TashkentChilanzarskiy rayon": "Chilanzar",
    "Chilanzarskiy rayon": "Chilanzar",
    "ТашкентЧиланзарский район": "Chilanzar",
    "Chilanzar": "Chilanzar",
    
    "TashkentAlmazarskiy rayon": "Almazar",
    "Almazarskiy rayon": "Almazar",
    "ТашкентАлмазарский район": "Almazar",
    "Almazar": "Almazar",
    
    "TashkentMirzo-Ulugbekskiy rayon": "Mirzo-Ulugbek",
    "Mirzo-Ulugbekskiy rayon": "Mirzo-Ulugbek",
    "ТашкентМирзо-Улугбекский район": "Mirzo-Ulugbek",
    "Mirzo-Ulugbek": "Mirzo-Ulugbek",
    
    "TashkentShayhantahurskiy rayon": "Shayhantahur",
    "Shayhantahurskiy rayon": "Shayhantahur",
    "ТашкентШайхантахурский район": "Shayhantahur",
    "Shayhantahur": "Shayhantahur",
    
    "TashkentYashnabadskiy rayon": "Yashnabad",
    "Yashnabadskiy rayon": "Yashnabad",
    "ТашкентЯшнабадский район": "Yashnabad",
    "Yashnabad": "Yashnabad",
    
    "TashkentUchtepinskiy rayon": "Uchtepa",
    "Uchtepinskiy rayon": "Uchtepa",
    "ТашкентУчтепинский район": "Uchtepa",
    "Uchtepa": "Uchtepa",
    
    "TashkentBektemirskiy rayon": "Bektemir",
    "Bektemirskiy rayon": "Bektemir",
    "ТашкентБектемирский район": "Bektemir",
    "Bektemir": "Bektemir",
    
    "TashkentYakkasarayskiy rayon": "Yakkasaray",
    "Yakkasarayskiy rayon": "Yakkasaray",
    "ТашкентЯккасарайский район": "Yakkasaray",
    "Yakkasaray": "Yakkasaray",
    
    "TashkentMirabadskiy rayon": "Mirab",
    "Mirabadskiy rayon": "Mirab",
    "ТашкентМирабадский район": "Mirab",
    "Mirab": "Mirab",
    "Mirabad": "Mirab",
    
    # SAMARKAND REGION
    "Samarkand": "Samarkand",
    "Самарканд": "Samarkand",
    "Urgut": "Urgut",
    "Ургут": "Urgut",
    "Kattakurgan": "Kattakurgan",
    "Каттакурган": "Kattakurgan",
    "Bulungur": "Bulungur",
    "Булунгур": "Bulungur",
    "Panjob": "Panjob",
    "Jomboy": "Jomboy",
    "Джамбай": "Jomboy",
    "Dzhambay": "Jomboy",
    "Narpay": "Narpay",
    "Payariq": "Payariq",
    "Payshanba": "Payshanba",
    "Gazalkent": "Gazalkent",
    "Газалкент": "Gazalkent",
    
    # BUKHARA REGION
    "Buhara": "Bukhara",
    "Bukhara": "Bukhara",
    "Бухара": "Bukhara",
    "Gizhduvan": "Gizhduvan",
    "Гиждуван": "Gizhduvan",
    "Galaasiya": "Galaasiya",
    "Галаасия": "Galaasiya",
    "Karakul": "Karakul",
    "Каракуль": "Karakul",
    "Karmana": "Karmana",
    "Кармана": "Karmana",
    "Kagan": "Kagan",
    "Каган": "Kagan",
    "Romitan": "Romitan",
    "Ромитан": "Romitan",
    "Shafirkan": "Shafirkan",
    "Шафиркан": "Shafirkan",
    "Vabkent": "Vabkent",
    "Вабкент": "Vabkent",
    "Eshanguzar": "Eshanguzar",
    "Эшангузар": "Eshanguzar",
    "Koshkupyr": "Koshkupyr",
    "Nurafshan (Toytepa)": "Nurafshan",
    "Нурафшан (Тойтепа)": "Nurafshan",
    "Nurata": "Nurata",
    "Нурата": "Nurata",
    
    # FERGANA REGION
    "Fergana": "Fergana",
    "Фергана": "Fergana",
    "Kokand": "Kokand",
    "Коканд": "Kokand",
    "Margilan": "Margilan",
    "Маргилан": "Margilan",
    "Yangi Margilan": "Margilan",
    "Янги Маргилан": "Margilan",
    "Rishtan": "Rishtan",
    "Риштан": "Rishtan",
    "Bustan": "Bustan",
    "Бустан": "Bustan",
    "Kuva": "Quva",
    "Кува": "Quva",
    "Quva": "Quva",
    "Kuvasay": "Quvasoy",
    "Кувасай": "Quvasoy",
    "Quvasoy": "Quvasoy",
    "Andizhan": "Andijan",
    "Андижан": "Andijan",
    "Asaka": "Asaka",
    "Асака": "Asaka",
    "Balykchi": "Baliqchi",
    "Балыкчи": "Baliqchi",
    "Yangiabad": "Yangiabad",
    "Chust": "Chust",
    "Чуст": "Chust",
    "Yoqoq": "Yoqoq",
    "Ozbekiston": "Ozbekiston",
    "Uychi": "Uychi",
    "Yo'qoq": "Yoqoq",
    "Keles": "Keles",
    "Келес": "Keles",
    "Iskandar": "Iskandar",
    "Iskandarkul": "Iskandarkul",
    
    # ANDIJAN REGION
    "Aldiariq": "Aldiariq",
    "Altiariq": "Altiariq",
    "Altiariq": "Altiariq",
    "Altyaryk": "Altiariq",
    "Алтыарык": "Altiariq",
    "Marhamat": "Marhamat",
    "Мархамат": "Marhamat",
    "Pahtaabad": "Pahtaabad",
    "Paxta-abad": "Pahtaabad",
    "Paxta-abad": "Pahtaabad",
    "Qorasuv": "Qorasuv",
    "Khonaabad": "Khonaabad",
    
    # NAMANGAN REGION
    "Namangan": "Namangan",
    "Наманган": "Namangan",
    "Chust": "Chust",
    "Чуст": "Chust",
    "Kosonsoy": "Kosonsoy",
    "Mingbul": "Mingbul",
    "Norin": "Norin",
    "Pop": "Pop",
    "Uchqorghon": "Uchqorghon",
    "Yangikurgan": "Yangikurgan",
    "Янгикурган": "Yangikurgan",
    "Navbahor": "Navbahor",
    "Turk'estan": "Turkestan",
    "Turkestan": "Turkestan",
    
    # KASHKADARYA REGION
    "Karshi": "Karshi",
    "Карши": "Karshi",
    "Carshi": "Karshi",
    "Ambul": "Ambul",
    "Chiroqchi": "Chiroqchi",
    "Chirakchi": "Chiroqchi",
    "Чиракчи": "Chiroqchi",
    "Dehkanabad": "Dehkanabad",
    "Дехканабад": "Dehkanabad",
    "Guzar": "Guzar",
    "Гузар": "Guzar",
    "Kasbi": "Kasbi",
    "Касби": "Kasbi",
    "Kitab": "Kitob",
    "Китаб": "Kitob",
    "Koson": "Koson",
    "Mubarek": "Mubarek",
    "Мубарек": "Mubarek",
    "Nishon": "Nishon",
    "Qamashi": "Qamashi",
    "Камаши": "Qamashi",
    "Shahrisabz": "Shahrisabz",
    "Шахрисабз": "Shahrisabz",
    "Shurchi": "Shurchi",
    "Шурчи": "Shurchi",
    "Yakkabag": "Yakkabag",
    "Яккабаг": "Yakkabag",
    "Yoshli": "Yoshli",
    "Zamin": "Zamin",
    "Zaamin": "Zamin",
    "Shargun": "Shargun",
    "Шаргунь": "Shargun",
    "Pitnak": "Pitnak",
    
    # SURKHANDARYA REGION
    "Termez": "Termiz",
    "Термез": "Termiz",
    "Angor": "Angor",
    "Ангор": "Angor",
    "Bandihon": "Bandihon",
    "Бандихон": "Bandihon",
    "Baysun": "Baysun",
    "Байсун": "Baysun",
    "Denau": "Denau",
    "Денау": "Denau",
    "Jarqorghon": "Jarqorghon",
    "Qiziriq": "Qiziriq",
    "Кизирик": "Qiziriq",
    "Kizirik": "Qiziriq",
    "Qumqorghon": "Qumqorghon",
    "Sariasiya": "Sariasoya",
    "Сариасия": "Sariasoya",
    "Sherabad": "Sherabad",
    "Шерабад": "Sherabad",
    "Shorchi": "Shorchi",
    "Шурчи": "Shorchi",
    "Shurchi": "Shorchi",
    "Surkhan": "Surkhan",
    "Uzun": "Uzun",
    "Узун": "Uzun",
    "Hodzheyli": "Hodzheyli",
    "Ходжейли": "Hodzheyli",
    "Sayhun": "Sayhun",
    "Сайхун": "Sayhun",
    "Payshanba": "Payshanba",
    "Пайшанба": "Payshanba",
    "Hankabad": "Hankabad",
    "Dangarah": "Dangara",
    "Dangara": "Dangara",
    "Дангара": "Dangara",
    "Ziadin": "Ziadin",
    "Зиадин": "Ziadin",
    "Dustlik": "Dustlik",
    "Дустлик": "Dustlik",
    
    # NAVOI REGION
    "Navoi": "Navoi",
    "Навои": "Navoi",
    "Qaragum": "Qaragum",
    "Konimex": "Konimex",
    "Nurata": "Nurata",
    "Нурата": "Nurata",
    "Tomdi": "Tomdi",
    "Uchkuduk": "Uchkuduk",
    "Учкудук": "Uchkuduk",
    "Zafarimni": "Zafarimni",
    "Akaltyn": "Akaltyn",
    "Aydarkul": "Aydarkul",
    
    # JIZZAKH REGION
    "Dzhizak": "Jizzakh",
    "Джизак": "Jizzakh",
    "Jizzakh": "Jizzakh",
    "Arnasoy": "Arnasoy",
    "Dostlik": "Dostlik",
    "Дустлик": "Dostlik",
    "Do'stlik": "Dostlik",
    "Forish": "Forish",
    "Galaba": "Galaba",
    "G'alaba": "Galaba",
    "Mirzachol": "Mirzachol",
    "Mirzacho'l": "Mirzachol",
    "Paxtakor": "Paxtakor",
    "Пахтакор": "Paxtakor",
    "Pahtakor": "Paxtakor",
    "Yangiobod": "Yangiobod",
    "Zafarabad": "Zafarabad",
    "Зафарабад": "Zafarabad",
    "Zarbdor": "Zarbdor",
    "Зарбдар": "Zarbdor",
    "Zarbdar": "Zarbdor",
    "Sardoba": "Sardoba",
    "Сардоба": "Sardoba",
    "Tamdybulak": "Tamdybulak",
    "Tамдыбулак": "Tamdybulak",
    "Yangiyor": "Yangiyor",
    "Syrdarya": "Syrdarya",
    "Сырдарья": "Syrdarya",
    "Cyrdarya": "Syrdarya",
    "Cырдарья": "Syrdarya",
    "Dzhuma": "Dzhuma",
    "Джума": "Dzhuma",
    "Dustabad": "Dustabad",
    "Zarafshan": "Zarafshan",
    "Зарафшан": "Zarafshan",
    "Gulistan": "Gulistan",
    "Гулистан": "Gulistan",
    "Karakul": "Karakul",
    "Karakul": "Karakul",
    "Kanylikul": "Kanylikul",
    "Kanlykul": "Kanylikul",
    
    # TASHKENT REGION
    "Chirchik": "Chirchik",
    "Чирчик": "Chirchik",
    "Yangiyul": "Yangiyul",
    "Янгиюль": "Yangiyul",
    "Angren": "Angren",
    "Ангрен": "Angren",
    "Ahangaran": "Ahangaran",
    "Ахангаран": "Ahangaran",
    "Bekabad": "Bekabad",
    "Бекабад": "Bekabad",
    "Gazalkent": "Gazalkent",
    "Газалкент": "Gazalkent",
    "Kibray": "Kibray",
    "Кибрай": "Kibray",
    "Pskent": "Pskent",
    "Пскент": "Pskent",
    "Tashkent": "Tashkent",
    "Ozarbayev": "Ozarbayev",
    
    # KARAKALPAKSTAN
    "Nukus": "Nukus",
    "Нукус": "Nukus",
    "Urgench": "Urgench",
    "Ургенч": "Urgench",
    "Amudarya": "Amudarya",
    "Beruniy": "Beruniy",
    "Берни": "Beruniy",
    "Beruni": "Beruniy",
    "Chimboy": "Chimboy",
    "Чимбай": "Chimboy",
    "Chimbay": "Chimboy",
    "Qanlikul": "Qanlikul",
    "Qorauzak": "Qorauzak",
    "Qongirot": "Qongirot",
    "Takhtakopir": "Takhtakopir",
    "Turtkul": "Turtkul",
    "Турткуль": "Turtkul",
    "Xojayli": "Xojayli",
    "Khojayli": "Xojayli",
    "Hiva": "Hiva",
    "Хива": "Hiva",
    "Khiva": "Hiva",
    "Hazarasp": "Hazarasp",
    "Хазарасп": "Hazarasp",
    "Muynak": "Muynak",
    "Gazli": "Gazli",
    "Kungrad": "Kungrad",
    "Kegeyli": "Kegeyli",
    "Jumbay": "Jumbay",
    "Zhondor": "Zhondor",
    "Жондор": "Zhondor",
    "Zangiata": "Zangiata",
    "Зангиата": "Zangiata",
    
    # SMALLER CITIES & DISTRICTS
    "Nazarbek": "Nazarbek",
    "Назарбек": "Nazarbek",
    "Almalyk": "Almalyk",
    "Алмалык": "Almalyk",
    "Parkent": "Parkent",
    "Паркент": "Parkent",
    "Karaul": "Karaul",
    "Караул": "Karaul",
    "Gyulabad": "Gyulabad",
    "Гюлабад": "Gyulabad",
    "Kyzyltepa": "Kyzyltepa",
    "Кызылтепа": "Kyzyltepa",
    "Yangibazar": "Yangibazar",
    "Янгибазар": "Yangibazar",
    "Koksaray": "Koksaray",
    "Коксарай": "Koksaray",
    "Guzalkent": "Guzalkent",
    "Гузалкент": "Guzalkent",
    "Tashmore": "Tashmore",
    "Ташморе": "Tashmore",
    "Karakul": "Karakul",
    "Hanka": "Hanka",
    "Ханка": "Hanka",
    "Darband": "Darband",
    "Dzharkurgan": "Dzharkurgan",
    "Tahiatash": "Tahiatash",
    "Тахиаташ": "Tahiatash",
    "Laish": "Laish",
    "Лаиш": "Laish",
    "Usmat": "Usmat",
    "Усмат": "Usmat",
    "Chartak": "Chartak",
    "Bagdad": "Bagdad",
    "Багдад": "Bagdad",
    "Yangier": "Yangier",
    "Янгиер": "Yangier",
    "Payaryk": "Payaryk",
    "Пайарык": "Payaryk",
    "Gurlen": "Gurlen",
    "Гурлен": "Gurlen",
    "Altyaryk": "Altyaryk",
    "Алтыарык": "Altyaryk",
    "Uchkyzyl": "Uchkyzyl",
    "Учкызыл": "Uchkyzyl",
    "Uchkuduk": "Uchkuduk",
    "Учкудук": "Uchkuduk",
    "Uchkuprik": "Uchkuprik",
    "Учкуприк": "Uchkuprik",
    "Uchkurgan": "Uchkurgan",
    "Dzhuma": "Dzhuma",
    "Джума": "Dzhuma",
    "Hodzhikent": "Hodzhikent",
    "Hodzhaabad": "Hodzhaabad",
    "Ходжаабад": "Hodzhaabad",
    "Kasansay": "Kasansay",
    "Касансай": "Kasansay",
    "Kasbi": "Kasbi",
    "Касби": "Kasbi",
    "Kasan": "Kasan",
    "Касан": "Kasan",
    "Chilek": "Chilek",
    "Чилек": "Chilek",
    "Chiliz": "Chilek",
    "Chinaz": "Chinaz",
    "Чиназ": "Chinaz",
    "Akkurgan": "Akkurgan",
    "Аккурган": "Akkurgan",
    "Aktash": "Aktash",
    "Акташ": "Aktash",
    "Alat": "Alat",
    "Алат": "Alat",
    "Beshkent": "Beshkent",
    "Бешкент": "Beshkent",
    "Besharyk": "Besharyk",
    "Beshrabat": "Beshrabat",
    "Бешрабат": "Beshrabat",
    "Buka": "Buka",
    "Бука": "Buka",
    "Bulakbashi": "Bulakbashi",
    "Булакбаши": "Bulakbashi",
    "Charvak": "Charvak",
    "Чарвак": "Charvak",
    "Dasht": "Dasht",
    "Dashtobod": "Dashtobod",
    "Даштобод": "Dashtobod",
    "Durmen": "Durmen",
    "Dzhigora": "Dzhigora",
    "Eshankol": "Eshankol",
    "Gagarin": "Gagarin",
    "Гагарин": "Gagarin",
    "Goliblar": "Goliblar",
    "Голиблар": "Goliblar",
    "Gulbahor": "Gulbahor",
    "Гульбахор": "Gulbahor",
    "Hamza": "Hamza",
    "Хамза": "Hamza",
    "Halkabad": "Halkabad",
    "Халкабад": "Halkabad",
    "Hakkulabad": "Hakkulabad",
    "Havast": "Havast",
    "Хаваст": "Havast",
    "Ishtyhan": "Ishtyhan",
    "Иштыхан": "Ishtyhan",
    "Kamanshi": "Kamanshi",
    "Kamashi": "Kamashi",
    "Кармана": "Kamashi",
    "Kanimeh": "Kanimeh",
    "Канимех": "Kanimeh",
    "Karashina": "Karashina",
    "Karasu": "Karasu",
    "Karaulbazar": "Karaulbazar",
    "Караулбазар": "Karaulbazar",
    "Karauzyak": "Karauzyak",
    "Caracol": "Caracol",
    "Carluk": "Carluk",
    "Karluk": "Carluk",
    "Карлук": "Carluk",
    "Chalysh": "Chalysh",
    "Чалыш": "Chalysh",
    "Chirakchi": "Chirakchi",
    "Чиракчи": "Chirakchi",
    "Cukok": "Cukok",
    "Cукок": "Cukok",
    "Chusti": "Chust",
    "Denau": "Denau",
    "Dhigora": "Dhigora",
    "Uchkurgan": "Uchkurgan",
    "Kumkurgan": "Kumkurgan",
    "Кумкурган": "Kumkurgan",
    "Kurgantepa": "Kurgantepa",
    "Кургантепа": "Kurgantepa",
    "Kuyganyar": "Kuyganyar",
    "Куйганъяр": "Kuyganyar",
    "Koshkupyr": "Koshkupyr",
    "Kosonsoy": "Kosonsoy",
    "Kushrabad": "Kushrabad",
    "Кушрабад": "Kushrabad",
    "Langar": "Langar",
    "Лангар": "Langar",
    "Mangit": "Mangit",
    "Мангит": "Mangit",
    "Mardzhanbulak": "Mardzhanbulak",
    "Марджанбулак": "Mardzhanbulak",
    "Mirishkor": "Mirishkor",
    "Yangi Mirishkor": "Mirishkor",
    "Muglan": "Muglan",
    "Муглан": "Muglan",
    "Muzrabad": "Muzrabad",
    "Navruz": "Navruz",
    "Навруз": "Navruz",
    "Nurabad": "Nurabad",
    "Нурабад": "Nurabad",
    "Pap": "Pap",
    "Пап": "Pap",
    "Pahtaabad": "Pahtaabad",
    "Paytug": "Paytug",
    "Пайтуг": "Paytug",
    "Ravan": "Ravan",
    "Salar": "Salar",
    "Салар": "Salar",
    "Saryk": "Saryk",
    "Сарык": "Saryk",
    "Shafirkan": "Shafirkan",
    "Shahrihan": "Shahrihan",
    "Шахрихан": "Shahrihan",
    "Shavat": "Shavat",
    "Шават": "Shavat",
    "Sheron": "Sheron",
    "Shahimardan": "Shahimardan",
    "Shumanay": "Shumanay",
    "Shurkhan": "Shurkhan",
    "Shirin": "Shirin",
    "Ширин": "Shirin",
    "Tashlak": "Tashlak",
    "Ташлак": "Tashlak",
    "Tashbulak": "Tashbulak",
    "Ташбулак": "Tashbulak",
    "Taylak": "Taylak",
    "Тайлак": "Taylak",
    "Terenozek": "Terenozek",
    "Talimardzhan": "Talimardzhan",
    "Turakurgan": "Turakurgan",
    "Туракурган": "Turakurgan",
    "Urtaaul": "Urtaaul",
    "Уртааул": "Urtaaul",
    "Yangi-Nishan": "Yangi-Nishan",
    "Янги-Нишан": "Yangi-Nishan",
    "Yangiabod": "Yangiabod",
    "Yangikishlak": "Yangikishlak",
    "Янгикишлак": "Yangikishlak",
    "Yangirabat": "Yangirabat",
    "Янгирабат": "Yangirabat",
    "Yaypan": "Yaypan",
    "Яйпан": "Yaypan",
    "Yazyavan": "Yazyavan",
    "Язъяван": "Yazyavan",
    "Zafar": "Zafar",
    "Zarbdar": "Zarbdar",
    "Zarbdar": "Zarbdar",
    "Baht": "Baht",
    "Бахт": "Baht",
    "Bayaut": "Bayaut",
    "Баяут": "Bayaut",
    "Bolshoy Chimgan": "Bolshoy Chimgan",
    "Bulungur": "Bulungur",
    "Булунгур": "Bulungur",
    "Cyllak": "Chilek",
    "Ahunbabaev": "Ahunbabaev",
    "Akmangit": "Akmangit",
    "Altynkul": "Altynkul",
    "Алтынкуль": "Altynkul",
    "Balandchakir": "Balandchakir",
    "Bagat": "Bagat",
    "Бандихон": "Bagat",
    "Boz": "Boz",
    "Боз": "Boz",
    "Krasnogorsk": "Krasnogorsk",
    "Красногорск": "Krasnogorsk",
    "Kumkurgan": "Kumkurgan",
    "Kymurgon": "Kumkurgan",
    "Dzhigora": "Dzhigora",
    "Djigora": "Dzhigora",
    "Eshankul": "Eshankul",
    "Gallaaral": "Gallaaral",
    "Gallaaral": "Gallaaral",
    "Qomur-Soy": "Qomur-Soy",
    "Sherabad": "Sherabad",
    "Tahtakupyr": "Tahtakupyr",
    "Talimardzhan": "Talimardzhan",
    "Terenozek": "Terenozek",
    "Vuadil": "Vuadil",
    }
    import re

    df['district_clean'] = df['district'].replace(correction_dict)

    def normalize_district(x):
        x = str(x).strip()
        x = re.sub(r'район|rayon', '', x, flags=re.IGNORECASE)
        x = x.replace('Tashkent', '')
        return x.strip()


    df['district'] = df['district_clean'].apply(normalize_district)
    print(df['district'].value_counts().head(5))
    return df


