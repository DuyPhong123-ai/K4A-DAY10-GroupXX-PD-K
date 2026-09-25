from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


REQUIRED_COLUMNS = {
   "paper_id",
   "title",
   "summary",
   "authors_joined",
   "published",
   "categories_joined",
}


def _text(value: Any, fallback: str = "Unknown") -> str:
   if value is None or pd.isna(value):
      return fallback
   cleaned = normalize_whitespace(str(value))
   return cleaned or fallback


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
   """Build a deterministic ten-question benchmark from cleaned papers."""
   missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
   if missing_columns:
      raise ValueError(f"Cannot build evaluation set; missing columns: {', '.join(missing_columns)}")
   if len(df) < 10:
      raise ValueError(f"At least 10 documents are required to build the test set; received {len(df)}.")

   question_types = [
      "summary",
      "authors",
      "date",
      "categories",
      "summary",
      "authors",
      "date",
      "categories",
      "summary",
      "authors",
   ]
   test_set: list[dict[str, Any]] = []
   for question_number, (row_index, question_type) in enumerate(
      zip(range(10), question_types, strict=True),
      start=1,
   ):
      row = df.iloc[row_index]
      paper_id = _text(row["paper_id"])
      title = _text(row["title"])
      summary = _text(row["summary"])
      authors = _text(row["authors_joined"])
      published = _text(row["published"])
      categories = _text(row["categories_joined"])

      if question_type == "summary":
         question = f"What is the main summary of the paper '{title}'?"
         ground_truth = first_sentence(summary)
      elif question_type == "authors":
         question = f"Who are the authors of the paper '{title}'?"
         ground_truth = authors
      elif question_type == "date":
         question = f"When was the paper '{title}' published?"
         ground_truth = published
      else:
         question = f"What categories describe the paper '{title}'?"
         ground_truth = categories

      test_set.append(
         {
            "id": f"eval_{question_number:03d}",
            "question_type": question_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
         }
      )

   write_json(output_path, test_set)
   return test_set
