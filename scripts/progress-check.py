import json
import os
from collections import Counter

import dotenv
import pandas as pd
import sqlalchemy

dotenv.load_dotenv(".env")

engine = sqlalchemy.create_engine(os.getenv("PGCONN"))

examples = pd.read_sql_table("example", con=engine)

annotator_ids = []
for i, row in examples.iterrows():
    content = json.loads(row["content"])
    annotator_id = content["_annotator_id"]
    if annotator_id.startswith("ume-final"):
        annotator_ids.append(annotator_id)

print(f"Total annotations: {len(annotator_ids)}")
print(Counter(annotator_ids))
