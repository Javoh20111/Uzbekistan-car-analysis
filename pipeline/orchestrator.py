import pandas as pd
import numpy as np

def extractor():
    df = pd.read_json('data/raw/car_data.json')
    return df

from transformation import duplicate_remover, model_cleaner

def main():
    df = extractor()
    df = duplicate_remover(df)
    df = model_cleaner(df)



if "__main__" == __name__:
    main()