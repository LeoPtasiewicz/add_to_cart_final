import pandas as pd
import os
import ast


def safe_literal_eval(val):
    if isinstance(val, str):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return []
    return val

def join_exports():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    export_path = os.path.join(script_dir, 'exports', 'export.csv')
    reference_path = os.path.join(script_dir, 'exports', 'reference_file.csv')
    
    # Read CSV files
    export_df = pd.read_csv(export_path)
    reference_df = pd.read_csv(reference_path, usecols=['prizeid', 'new_url'])

    # Convert Allprizeids to list
    export_df['Allprizeids'] = export_df['Allprizeids'].apply(safe_literal_eval)

    # Function to find matching new_url
    def find_matching_url(allprizeids):
        matching_urls = reference_df[reference_df['prizeid'].isin(allprizeids)]['new_url'].dropna().tolist()
        return ', '.join(matching_urls) if matching_urls else ''

    # Apply the function to get matching new_url
    export_df['matching_new_url'] = export_df['Allprizeids'].apply(find_matching_url)

    # Save the result
    output_path = os.path.join(script_dir, 'exports', 'combined_order_details.csv')
    export_df.to_csv(output_path, index=False)
    print(f"Output saved as: {output_path}")

    # Print some statistics
    print(f"Total rows in export_df: {len(export_df)}")
    print(f"Rows with matching new_url: {(export_df['matching_new_url'] != '').sum()}")
    print(f"Rows without matching new_url: {(export_df['matching_new_url'] == '').sum()}")
    combined_df = pd.read_csv(output_path)
    filtered_df = export_df[export_df['matching_new_url'] == '']
    for index, row in filtered_df.iterrows():
        print(f"Name: {row['Name']}, Game name: {row['Game name']}")

    aggregated_output_file = os.path.join(script_dir, 'exports', 'aggregated_order_details.csv')

    if os.path.exists(aggregated_output_file):
        os.remove(aggregated_output_file)
        print(f"Deleted existing file: {aggregated_output_file}")

    # Aggregate data to get unique URLs and their corresponding quantities
    aggregated_df = combined_df.groupby(['matching_new_url', 'Name']).size().reset_index(name='Quantity')
    aggregated_df = aggregated_df.sort_values('Quantity', ascending=False)

    # Save the aggregated data to a new CSV file
    aggregated_df.to_csv(aggregated_output_file, index=False)
    print(f"Aggregated data saved to {aggregated_output_file}")

# login()
join_exports()