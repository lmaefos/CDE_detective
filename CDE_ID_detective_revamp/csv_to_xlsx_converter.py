import os
import glob
import pandas as pd

def convert_each_csv(input_folder: str, output_folder: str = None):
    """
    Reads every .csv in `input_folder` and writes each out as a separate
    .xlsx file (same name, different extension) into `output_folder`
    (defaults to the same folder as the CSVs).
    """
    # If no explicit output folder given, use the input folder
    if output_folder is None:
        output_folder = input_folder
    os.makedirs(output_folder, exist_ok=True)

    pattern = os.path.join(input_folder, '*.csv')
    csv_paths = glob.glob(pattern)
    if not csv_paths:
        print(f"No CSV files found in {input_folder}")
        return

    for csv_path in csv_paths:
        base = os.path.splitext(os.path.basename(csv_path))[0]
        out_path = os.path.join(output_folder, f"{base}.xlsx")

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"⚠️ Skipping {csv_path!r}: {e}")
            continue

        df.to_excel(out_path, index=False)
        print(f"✅ Converted `{base}.csv` → `{base}.xlsx`")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert all CSVs in a folder to individual XLSX files."
    )
    parser.add_argument(
        'input_dir',
        help="Path to the folder containing your .csv files"
    )
    parser.add_argument(
        '-o', '--output-dir',
        help="Where to save the .xlsx files (defaults to input folder)",
        default=None
    )
    args = parser.parse_args()

    convert_each_csv(args.input_dir, args.output_dir)