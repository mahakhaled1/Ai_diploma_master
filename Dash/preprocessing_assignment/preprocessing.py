import pandas as pd


def Read_data_file(file_path):
    try:
        df = pd.read_csv(file_path)
        return df

    except FileNotFoundError:
        print("Error: File not found.")
        return None

    except Exception as e:
        print(f"Error reading the file: {e}")
        return None


def Drop_unnecessary_features(df, cols_to_drop):
    try:
        df = df.drop(columns=cols_to_drop)
        return df

    except KeyError as e:
        print(f"Error: Column not found: {e}")
        return df


def Check_data_type(df):
    report = pd.DataFrame({
        "Column Name": df.columns,
        "Data Type": df.dtypes.astype(str),
        "Number of Unique Values": df.nunique()
    })

    return report.T