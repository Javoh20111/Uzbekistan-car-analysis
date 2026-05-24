import pandas as pd
import numpy as np

def extractor():
    df = pd.read_json('data/raw/car_data.json')
    return df

from transformation import duplicate_remover, model_cleaner, price_validatetor, mileage_cleaner, engine_volume_cleaner, owners_count_cleaner, seller_type_cleaner

def main():
    df = extractor()
    print("\n"+"-"*40)
    df = duplicate_remover(df)
    print("-"*40+"\n")

    print("-"*40)
    df = model_cleaner(df)
    print("-"*40+"\n")

    print("-"*40)
    df = price_validatetor(df)
    print("-"*40+"\n")

    print("-"*40)
    df = mileage_cleaner(df)
    print("-"*40+"\n")

    print("-"*40)
    df = engine_volume_cleaner(df)
    print("-"*40+"\n")

    print("-"*40)
    df = owners_count_cleaner(df)
    print("-"*40+"\n")

    print("-"*40)
    df = seller_type_cleaner(df)
    print("-"*40+"\n")

if "__main__" == __name__:
    main()