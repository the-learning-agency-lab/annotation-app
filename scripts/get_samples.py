import os
import subprocess

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["PRODIGY_CONFIG"] = "prodigy-production.json"

dataset_names = ["ume-final", "ume2"]

dfs = []
for name in dataset_names:
    # Get data from Prodigy
    # subprocess.run(["prodigy", "db-out", name, "data"])

    # Load data
    dfs.append(pd.read_json(f"data/{name}.jsonl", lines=True))

df = pd.concat(dfs)

# Read in all items
all_items = pd.read_csv("data/ume-full-item-set.csv")

# Already adjudicated (outside of Prodigy)
already_adjudicated = pd.read_csv("data/Mar6data_ToAdjudicate.csv")

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
df["overall"] = pd.to_numeric(df["overall"], errors="coerce")
df["topic"] = pd.to_numeric(df["topic"], errors="coerce")
df["vocabulary"] = pd.to_numeric(df["vocabulary"], errors="coerce")
df["choices"] = pd.to_numeric(df["choices"], errors="coerce")


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
for_completion = all_items[all_items["idx"].isin(for_completion_idx)]
for_completion.to_json(
    "inputs/ume-rating/subset-2b.jsonl", orient="records", lines=True
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
    df[
        ~(df["idx"].isin(for_completion_idx))
        & ~(df["idx"].isin(already_adjudicated["idx"]))
    ]
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
    "inputs/ume-adjudication/subset-2.jsonl", orient="records", lines=True
)

# Subset-3
all_approved_items = pd.read_csv("data/AllProblemsToRetain_ExceptSubset1.csv")

subset_3 = all_approved_items[
    ~all_approved_items["idx"].isin(df["idx"])
]

subset_3.to_json(
    "inputs/ume-rating/subset-3.jsonl", orient="records", lines=True
)
