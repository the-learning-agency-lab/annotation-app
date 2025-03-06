import os
import subprocess

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["PRODIGY_CONFIG"] = "prodigy-production.json"

subprocess.run(["prodigy", "db-out", "ume-final", "data"])

df = pd.read_json(
    "data/ume-final.jsonl",
    lines=True,
)

df = df.drop(
    columns=[
        "display_question",
        "display_choice_A",
        "display_choice_B",
        "display_choice_C",
        "display_choice_D",
        "html",
        "_input_hash",
    ]
)

# Convert dtypes
df = df.replace('', pd.NA)
df["overall"] = df["overall"].astype("Int64")
df["topic"] = df["topic"].astype("Int64")
df["vocabulary"] = df["vocabulary"].astype("Int64")
df["choices"] = df["choices"].astype("Int64")

# Find rows with full responses
valid_values = [1, 2, 3]
validation_mask = (
    (df["overall"].isin(valid_values)) &
    (df["topic"].isin(valid_values)) &
    (df["vocabulary"].isin(valid_values)) &
    (df["choices"].isin(valid_values))
)

print(f"Valid annotations: {validation_mask.sum()}")

# Create a boolean mask to find rows with any differing choices
diff_mask = (
    (df['question'] != df['question_orig']) |
    (df['choice_A'] != df['choice_A_orig']) |
    (df['choice_B'] != df['choice_B_orig']) |
    (df['choice_C'] != df['choice_C_orig']) |
    (df['choice_D'] != df['choice_D_orig'])
)


def filter_bad_scores(group):
    """Filter out rows with bad scores."""
    return (
        (all(group["overall"] > 1)) &
        (all(group["topic"] > 1)) &
        (all(group["vocabulary"] > 1)) &
        (all(group["choices"] > 1))
    )


def consolidate_revisions(group):
    """Consolidate multiple revisions into a single row.
    By replacing the original values with the latest revision.
    """
    row = group.iloc[0].copy()
    if len(group) > 1:
        revision_2 = group.iloc[1]
        row["question_orig"] = revision_2["question"]
        row["choice_A_orig"] = revision_2["choice_A"]
        row["choice_B_orig"] = revision_2["choice_B"]
        row["choice_C_orig"] = revision_2["choice_C"]
        row["choice_D_orig"] = revision_2["choice_D"]
    return row


for_adjudication = (
    df[validation_mask & diff_mask]
    .drop(
        columns=[
            "_timestamp",
            "_annotator_id",
            "_session_id",
            "_view_id",
        ]
    )
    .groupby("idx")
    .filter(filter_bad_scores)
    .groupby("idx")
    .apply(consolidate_revisions, include_groups=False)
)

# Save samples for adjudication
print(f"For adjudication: {len(for_adjudication)}")
for_adjudication.to_json(
    "data/subset-1a-adjudication.jsonl",
    orient="records",
    lines=True
)

# Save samples with incomplete responses
for_completion = (
    df[~validation_mask]
    .drop(
        columns=[
            "_timestamp",
            "_annotator_id",
            "_session_id",
            "_view_id",
        ]
    )
)

print(f"For completion: {len(for_completion)}")
for_completion.to_json(
    "inputs/ume/subset-1b.jsonl",
    orient="records",
    lines=True
)
