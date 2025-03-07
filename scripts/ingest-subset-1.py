from pathlib import Path

import pandas as pd

input_file = Path('data/subset-1.csv')
output_file = Path('inputs') / 'ume-rating' / input_file.with_suffix('.jsonl').name
df = pd.read_csv(input_file)

# Shuffle the data
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"Writing to {output_file}")
df.to_json(output_file, orient='records', lines=True)
print("Done!")
