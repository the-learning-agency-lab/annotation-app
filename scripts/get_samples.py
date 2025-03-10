import os
import subprocess

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["PRODIGY_CONFIG"] = "prodigy-production.json"

# Download subset 1 annotations
# subprocess.run(["prodigy", "db-out", "ume-final", "data"])

# Load subset 1 annotations
df = pd.read_json(
    "data/ume-final.jsonl",
    lines=True,
)

# Read in subset 1 items
subset_1 = pd.read_csv("data/subset-1.csv")

# Drop unneeded columns
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
        "_session_id",
        "_view_id",
    ]
)

# Convert dtypes
df = df.replace("", pd.NA)
df["overall"] = df["overall"].astype("Int64")
df["topic"] = df["topic"].astype("Int64")
df["vocabulary"] = df["vocabulary"].astype("Int64")
df["choices"] = df["choices"].astype("Int64")


# Filter samples with less than two complete responses from different annotators
def filter_incomplete_responses(group):
    """Filter out rows with less than two complete responses from
    different annotators."""
    valid_values = [1, 2, 3]
    valid_group = group[
        group["overall"].isin(valid_values)
        & group["topic"].isin(valid_values)
        & group["vocabulary"].isin(valid_values)
        & group["choices"].isin(valid_values)
    ]

    if valid_group["_annotator_id"].nunique() >= 2:
        return False

    return True


for_completion_idx = (
    df.groupby("idx")
    .filter(filter_incomplete_responses)
    .drop(
        columns=[
            "_timestamp",
            "_annotator_id",
        ]
    )["idx"]
    .unique()
)

print(f"For completion: {len(for_completion_idx)}")
for_completion = subset_1[subset_1["idx"].isin(for_completion_idx)]
for_completion.to_json(
    "inputs/ume-rating/subset-1b.jsonl", orient="records", lines=True
)


def filter_for_adjudication(group):
    """Filter out rows with high agreement."""

    # Ignore incomplete annotations
    group = group[
        group["overall"].notna()
        & group["topic"].notna()
        & group["vocabulary"].notna()
        & group["choices"].notna()
    ]

    # If multiple complete annotations from the same annotator, choose the earliest
    group = group.sort_values("_timestamp", ascending=True).drop_duplicates(
        subset=["_annotator_id"]
    )

    # If less than two complete annotations, return False
    if len(group) < 2:
        return False
    elif len(group) > 2:
        group = group.head(2)

    # Boolean mask indicating that both annotators rated the item higher than 1
    overall_greater_than_one = all(group["overall"] > 1)

    # Boolean mask indicating that both annotators did NOT rate the item as 3
    overall_not_three = not all(group["overall"] == 3)

    return overall_greater_than_one and overall_not_three


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
    df[~df["idx"].isin(for_completion_idx)]
    .groupby("idx")
    .filter(filter_for_adjudication)
    .drop(
        columns=[
            "_timestamp",
            "_annotator_id",
        ]
    )
    .groupby("idx")
    .apply(consolidate_revisions, include_groups=False)
    .reset_index()  # Get the idx back as a column
)

assert not any(
    for_adjudication["idx"].isin(for_completion_idx)
), "Adjudication and completion samples overlap"

# Save samples for adjudication
print(f"For adjudication: {len(for_adjudication)}")
for_adjudication.to_json(
    "inputs/ume-adjudication/subset-1a.jsonl", orient="records", lines=True
)
