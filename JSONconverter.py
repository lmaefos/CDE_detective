import pandas as pd
import numpy as np
import json
import os

def preprocess_delimited_values(df, column_name, delimiter=";"):
    # Check if the column exists in DataFrame
    if column_name in df.columns:
        # Split the string into a list based on the delimiter
        df[column_name] = df[column_name].apply(lambda x: x.split(delimiter) if isinstance(x, str) else x)

def file_to_json(file_path, output_json_path, columns_to_split=None):
    # Determine the file extension
    _, file_extension = os.path.splitext(file_path)

    # Load the file based on its extension
    if file_extension in ['.xls', '.xlsx']:
        # For Excel files
        df = pd.read_excel(file_path, engine='openpyxl')
    elif file_extension == '.csv':
        # For CSV files
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Unsupported file type")

    # Replace NaN values with None (which becomes 'null' in JSON)
    df = df.replace({pd.NA: None})

    # Process delimited columns if specified
    if columns_to_split:
        for column, delimiter in columns_to_split.items():
            preprocess_delimited_values(df, column, delimiter)

    # Convert the DataFrame to a list of dictionaries (suitable for JSON)
    data = df.to_dict(orient='records')

    # Save the data to a JSON file
    with open(output_json_path, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"JSON file created at: {output_json_path}")

# Example usage
if __name__ == "__main__":
    file_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\Core_CDEs_and_abbreviations_Stewards.csv'
    output_json_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\Core_CDEs_and_abbreviations_Stewards.json'
    # Specify columns that contain delimited strings and their delimiters
    columns_to_process = {'Permissible Values': ';'}  # # Use the exact column name including spaces
    file_to_json(file_path, output_json_path, columns_to_process)
