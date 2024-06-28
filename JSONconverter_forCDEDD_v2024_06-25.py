import pandas as pd
import json

def excel_to_json(excel_file, sheet_name):
    # Load the Excel file
    df = pd.read_excel(excel_file, sheet_name=sheet_name)

    # Initialize an empty dictionary to hold all the data
    data = {}

    # Initialize a variable to keep track of the current CDE entry
    current_variable_name = None

    # Helper function to replace NaN with None
    def replace_nan(value):
        if pd.isna(value):
            return None
        return value

    # Iterate over each row in the DataFrame
    for _, row in df.iterrows():
        if pd.notna(row["CDE Name"]):
            # New CDE entry
            variable_name = row["Variable Name"]

            # Initialize a new entry if Variable Name is found
            if variable_name not in data:
                data[variable_name] = {
                    "Study Population Focus": replace_nan(row["Study Population Focus"]),
                    "Domain": replace_nan(row["Domain"]),
                    "CRF Question #": replace_nan(row["CRF Question #"]),
                    "CDE Name": replace_nan(row["CDE Name"]),
                    "Variable Name": replace_nan(row["Variable Name"]),
                    "Definition": replace_nan(row["Definition"]),
                    "Short Description": replace_nan(row["Short Description"]),
                    "Additional Notes (Question Text)": replace_nan(row["Additional Notes (Question Text)"]),
                    "Permissible Values": row["Permissible Values"].split(';') if pd.notna(row["Permissible Values"]) else [],
                    "PV Description": row["PV Description"].split(';') if pd.notna(row["PV Description"]) else [],
                    "Data Type": replace_nan(row["Data Type"]),
                    "Disease Specific Instructions": replace_nan(row["Disease Specific Instructions"]),
                    "Disease Specific References": row["Disease Specific References"].split(';') if pd.notna(row["Disease Specific References"]) else [],
                    "Population": replace_nan(row["Population"]),
                    "Classification": replace_nan(row["Classification"]),
                    "External Id CDISC": replace_nan(row["External Id CDISC"]),
                    "CDISC Permissible Values": replace_nan(row["CDISC Permissible Values"]),
                    "CDISC Data Type": replace_nan(row["CDISC Data Type"]),
                    "CDISC Notes": replace_nan(row["CDISC Notes"]),
                    "Additional Information": replace_nan(row["Additional Information"]),
                    "Map to CDISC variable name if different": replace_nan(row["Map to CDISC variable name if different"]),
                    "Map to CDISC format": replace_nan(row["Map to CDISC format"]),
                    "Notes": replace_nan(row["Notes"])
                }

            current_variable_name = variable_name

        else:
            # If CDE Name is blank, it's an answer choice for the previous entry
            if current_variable_name is not None:
                if pd.notna(row["Variable Name"]):
                    data[current_variable_name]["Permissible Values"].append(row["Variable Name"])
                if pd.notna(row["PV Description"]):
                    data[current_variable_name]["PV Description"].append(row["PV Description"])

    # Convert the dictionary to a JSON string
    json_data = json.dumps(data, indent=4)

    return json_data

# File to convert
excel_file = r"C:\Users\lmaefos\Code Stuffs\CDE_detective\Compiled_CORE_CDEs list_English_one sheet_as of 2024-06-25.xlsx"
sheet_name = "ALL"  # Change this to the actual sheet name if it's different
json_output = excel_to_json(excel_file, sheet_name)

# Define the output file path
output_file_path = r"C:\Users\lmaefos\Code Stuffs\CDE detective\output.json"

# Save the JSON output to a file
with open("output.json", "w") as json_file:
    json_file.write(json_output)

print("Excel data has been converted to JSON and saved to output.json")