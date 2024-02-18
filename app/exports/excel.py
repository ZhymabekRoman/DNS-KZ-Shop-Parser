import json
import pandas as pd

def export_to_excel(input_filename: str, output_filename: str):
    with open(input_filename) as json_file:
        data = json.load(json_file)
        
    df = pd.json_normalize(data, record_path=['products'], meta=['title', 'item_count'])
    
    def create_human_readable_summary(groups):
        summary = []
        for group in groups:
            group_title = group['title']
            specs_summary = '; '.join([f"{spec['title']}: {spec['value']}" for spec in group['specs']])
            summary.append(f"{group_title} - {specs_summary}")
        return '\n'.join(summary)
    
    df['extra_groups_summary'] = df.apply(lambda row: create_human_readable_summary(row['extra.groups']), axis=1)

    df.to_excel(output_filename, index=True, engine='openpyxl')