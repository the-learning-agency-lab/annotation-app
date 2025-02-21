import numpy as np
import pandas as pd

df = pd.read_csv('data/ume-full-item-set.csv')

# Shuffle the data
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Most samples will be reviewed by 1 annotator
df['n_annotators'] = 1

# Assign the first 100 rows to "0" annotators
# "0" means all annotators will review the sample
indices_for_zero = df.index.values[:100]
df.loc[indices_for_zero, 'n_annotators'] = 0

# Assign the next 200 rows to 2 annotators
indices_for_two = df.index.values[100:300]
df.loc[indices_for_two, 'n_annotators'] = 2
df.to_json('inputs/ume/full-item-set-annotators.jsonl',
           orient='records', lines=True)
