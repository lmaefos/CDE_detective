import pandas as pd
import numpy as np
import json
import os

def preprocess_delimited_values(df, column_name, delimiters):
    # Check if the column exists in DataFrame
    if column_name in df.columns:
        for delimiter in delimiters:
            # Split the string into a list based on the delimiter
            df[column_name] = df[column_name].apply(lambda x: x.split(delimiter) if isinstance(x, str) else x)

def detect_array_fields(df, delimiters):
    # Identify fields that should be arrays by checking for common delimiters
    array_fields = {}
    for column in df.columns:
        for delimiter in delimiters:
            if df[column].apply(lambda x: isinstance(x, str) and delimiter in x).any():
                array_fields[column] = delimiter
                break  # Stop after finding the first matching delimiter
    return array_fields

def file_to_json(file_path, output_json_path, columns_to_split=None, delimiters=[';', '|']):
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

    # Replace NaN and empty string values with None (which becomes 'null' in JSON)
    df = df.replace({pd.NA: None, '': None})

    # Automatically detect columns with delimited values if not provided
    if columns_to_split is None:
        columns_to_split = detect_array_fields(df, delimiters)

    # Process delimited columns
    if columns_to_split:
        for column, delimiter in columns_to_split.items():
            preprocess_delimited_values(df, column, [delimiter])

    # Convert the DataFrame to a list of dictionaries (suitable for JSON)
    data = df.to_dict(orient='records')

    # Group by the 'module' field
    grouped_data = {}
    for entry in data:
        module = entry.get('module')
        if module not in grouped_data:
            grouped_data[module] = []
        grouped_data[module].append(entry)

    # Save the data to a JSON file
    with open(output_json_path, 'w') as file:
        json.dump(grouped_data, file, indent=4)

    print(f"JSON file created at: {output_json_path}")

# Example usage
if __name__ == "__main__":
    file_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\SAMPLE_DataDictionary.csv'
    output_json_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\SAMPLE_DataDictionary.json'
    # Specify columns that contain delimited strings and their delimiters (optional, auto-detection included)
    columns_to_process = None  # {'Permissible Values': ';'}  # Example: Use the exact column name including spaces
    file_to_json(file_path, output_json_path, columns_to_process)