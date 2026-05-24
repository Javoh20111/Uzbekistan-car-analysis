import pandas as pd

from transformation import (
    duplicate_remover,
    engine_volume_cleaner,
    mileage_cleaner,
    model_cleaner,
    owners_count_cleaner,
    price_validatetor,
    seller_type_cleaner,
    year_cleaner,
)


TRANSFORMATIONS = [
    duplicate_remover,
    model_cleaner,
    price_validatetor,
    mileage_cleaner,
    engine_volume_cleaner,
    owners_count_cleaner,
    seller_type_cleaner,
    year_cleaner,
]


def extractor():
    df = pd.read_json('data/raw/car_data.json')
    return df


def run_transformations(df):
    for transform in TRANSFORMATIONS:
        print("\n" + "-" * 40)
        print(f"Running: {transform.__name__}")
        df = transform(df)
        print("-" * 40)

    return df


def main():
    df = extractor()
    df = run_transformations(df)

if "__main__" == __name__:
    main()
