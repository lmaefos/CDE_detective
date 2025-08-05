import os
import pandas as pd

# === CONFIG ===
folder_path = folder_path = r'C:\Users\lmaefos\Code Stuffs\CDE_detective\CDE_ID_detective_revamp\out' # Change if needed
output_file = 'combined_filtered_matches.xlsx'
target_sheet = 'EnhancedDD'
match_column = 'HEAL Core CRF Match'

# === SCRIPT ===
filtered_rows = []

for filename in os.listdir(folder_path):
    if filename.endswith('_matches_confirmed.xlsx'):
        file_path = os.path.join(folder_path, filename)
        
        try:
            df = pd.read_excel(file_path, sheet_name=target_sheet)
        except Exception as e:
            print(f"Skipping {filename} due to error: {e}")
            continue
        
        # Filter rows where HEAL Core CRF Match is NOT "No CRF match"
        df_filtered = df[df[match_column] != "No CRF match"].copy()

        # Add file identifier column
        df_filtered['Source_File'] = filename.replace('_matches_confirmed.xlsx', '')

        # Append to list
        filtered_rows.append(df_filtered)

# Combine all filtered data
if filtered_rows:
    combined_df = pd.concat(filtered_rows, ignore_index=True)
    combined_df.to_excel(os.path.join(folder_path, output_file), index=False)
    print(f"Filtered and combined file saved as: {output_file}")
else:
    print("No matching data found in any files.")
