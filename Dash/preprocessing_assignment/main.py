from preprocessing import (
    Read_data_file,
    Drop_unnecessary_features,
    Check_data_type
)

from config.config import COLS_TO_DROP

import os


file_path = os.path.join(os.path.dirname(__file__), "Titanic.csv")


# Read the dataset
df = Read_data_file(file_path)

if df is not None:

    print("Original Dataset:")
    print(df)

    # Check data types
    print("\nData Quality Report:")
    report = Check_data_type(df)
    print(report)

    # Remove unnecessary features
    df = Drop_unnecessary_features(df, COLS_TO_DROP)

    print("\nDataset After Removing Unnecessary Features:")
    print(df)