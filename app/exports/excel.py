import pandas as pd

def export_to_excel(input_filename: str, output_filename: str):
    result = pd.read_json(input_filename)
    
    flat_data = pd.json_normalize(result['products'])

    flat_data.to_excel(output_filename, index=False, engine='openpyxl')