import os
import subprocess

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["PRODIGY_CONFIG"] = "prodigy-production.json"

subprocess.run(["prodigy", "db-out", "ume", "data"])

df = pd.read_json("data/ume.jsonl", lines=True)
df = df.drop(
    columns=[
        "display_question",
        "display_choice_A",
        "display_choice_B",
        "display_choice_C",
        "display_choice_D",
        "html",
        "_input_hash",
        "_task_hash",
        ]
    )
df.to_json("data/ume.jsonl", orient="records", lines=True)