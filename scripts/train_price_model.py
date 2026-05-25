from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_PATH, MODEL_ARTIFACT_PATH
from src.price_model import save_price_model, train_price_model


def main():
    df = pd.read_csv(DATA_PATH)
    artifact = train_price_model(df)
    save_price_model(artifact, MODEL_ARTIFACT_PATH)

    metrics = artifact["metrics"]
    print(f"Saved model artifact: {MODEL_ARTIFACT_PATH}")
    print(f"Training rows: {metrics['training_rows']:,}")
    print(f"Testing rows: {metrics['testing_rows']:,}")
    print(f"MAE: ${metrics['mae']:,.0f}")
    print(f"RMSE: ${metrics['rmse']:,.0f}")
    print(f"R2: {metrics['r2']:.3f}")


if __name__ == "__main__":
    main()
