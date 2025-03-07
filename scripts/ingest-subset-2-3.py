from pathlib import Path

import pandas as pd

input_file = Path('data/AllProblemsToRetain_ExceptSubset1.csv')
output_2 = Path('inputs') / 'ume-rating' / 'subset-2.jsonl'
output_3 = Path('inputs') / 'ume-rating-single' / 'subset-3.jsonl'

df = pd.read_csv(input_file)

# Select Subsets
subset_2 = df.sample(n=158, random_state=42).reset_index(drop=True)
print(f"Subset 2: {len(subset_2)}")
print(f"Writing to {output_2}")
subset_2.to_json(output_2, orient='records', lines=True)


subset_3 = df[~df.index.isin(subset_2.index)].reset_index(drop=True)
print(f"Subset 3: {len(subset_3)}")
print(f"Writing to {output_3}")
subset_3.to_json(output_3, orient='records', lines=True)

print("Done!")
