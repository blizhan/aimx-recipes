"""Input file verification and strict CSV loading for Meta Kaggle."""

import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Sequence
import duckdb
from aimx_recipes.cli.output import (
    ERR_COLUMN_MISSING,
    ERR_CSV_MALFORMED,
    ERR_INPUT_CHANGED,
    ERR_INPUT_MISSING,
)

REQUIRED_INPUTS: dict[str, list[str]] = {
    "Competitions.csv": [
        "Id",
        "Slug",
        "Title",
        "Subtitle",
        "HostSegmentTitle",
        "EnabledDate",
        "DeadlineDate",
        "Overview",
        "EvaluationAlgorithmDescription",
        "DatasetDescription",
        "EvaluationAlgorithmAbbreviation",
        "EvaluationAlgorithmName",
        "EvaluationAlgorithmIsMax",
        "LicenseName",
    ],
    "Teams.csv": [
        "Id",
        "CompetitionId",
        "WriteUpForumTopicId",
        "Medal",
        "PublicLeaderboardRank",
        "PrivateLeaderboardRank",
    ],
    "ForumTopics.csv": [
        "Id",
        "Title",
        "FirstForumMessageId",
    ],
    "ForumMessages.csv": [
        "Id",
        "PostDate",
        "Message",
        "RawMarkdown",
    ],
    "Tags.csv": [
        "Id",
        "Name",
    ],
    "CompetitionTags.csv": [
        "Id",
        "CompetitionId",
        "TagId",
    ],
}


class InputError(Exception):
    """Raised when an input file is missing, changed, or invalid."""

    def __init__(
        self,
        code: str,
        message: str,
        file: str | None = None,
        line: int | None = None,
        record_id: str | None = None,
        column: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.file = file
        self.line = line
        self.record_id = record_id
        self.column = column

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.file:
            d["file"] = self.file
        if self.line is not None:
            d["line"] = self.line
        if self.record_id:
            d["record_id"] = self.record_id
        if self.column:
            d["column"] = self.column
        return d


@dataclass
class FileInput:
    name: str
    path: Path
    size_bytes: int
    sha256: str
    st_mtime_ns: int
    st_ino: int
    headers: list[str]
    row_count: int | None = None


def verify_inputs(meta_kaggle_dir: Path | str) -> list[FileInput]:
    """Verify presence, headers, and stat/fingerprint of the six required CSV files."""
    base = Path(meta_kaggle_dir)
    results: list[FileInput] = []

    for filename, required_cols in REQUIRED_INPUTS.items():
        file_path = base / filename
        if not file_path.exists() or not file_path.is_file():
            raise InputError(
                code=ERR_INPUT_MISSING,
                file=filename,
                message=f"Required Meta Kaggle file '{filename}' was not found in {base}",
            )

        st = file_path.stat()

        # Validate headers using csv.reader
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                header_row = next(reader, None)
        except Exception as e:
            raise InputError(
                code=ERR_CSV_MALFORMED,
                file=filename,
                line=1,
                message=f"Failed to read header of '{filename}': {e}",
            ) from e

        if not header_row:
            raise InputError(
                code=ERR_CSV_MALFORMED,
                file=filename,
                line=1,
                message=f"Empty header in file '{filename}'",
            )

        header_set = set(header_row)
        for req in required_cols:
            if req not in header_set:
                raise InputError(
                    code=ERR_COLUMN_MISSING,
                    file=filename,
                    column=req,
                    message=f"Required column '{req}' is missing in '{filename}'",
                )

        # Compute sha256
        with open(file_path, "rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()

        results.append(
            FileInput(
                name=filename,
                path=file_path,
                size_bytes=st.st_size,
                sha256=digest,
                st_mtime_ns=st.st_mtime_ns,
                st_ino=st.st_ino,
                headers=header_row,
            )
        )

    return results


def verify_stat_after(inputs: Sequence[FileInput]) -> None:
    """Verify that file stats have not changed between start of run and completion."""
    for inp in inputs:
        if not inp.path.exists():
            raise InputError(
                code=ERR_INPUT_CHANGED,
                file=inp.name,
                message=f"Input file '{inp.name}' disappeared during execution",
            )
        st = inp.path.stat()
        if (
            st.st_size != inp.size_bytes
            or st.st_mtime_ns != inp.st_mtime_ns
            or st.st_ino != inp.st_ino
        ):
            raise InputError(
                code=ERR_INPUT_CHANGED,
                file=inp.name,
                message=f"Input file '{inp.name}' changed during execution",
            )


def create_input_views(
    con: duckdb.DuckDBPyConnection,
    meta_kaggle_dir: Path | str,
    inputs: Sequence[FileInput],
) -> dict[str, int]:
    """Create strict DuckDB views for each CSV and return verified row counts."""
    row_counts: dict[str, int] = {}

    for inp in inputs:
        view_name = f"v_{Path(inp.name).stem.lower()}"
        col_items = ", ".join(
            [f"'{col.replace('\'', '\'\'')}': 'VARCHAR'" for col in inp.headers]
        )
        quoted_path = "'" + inp.path.as_posix().replace("'", "''") + "'"
        view_sql = f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT * FROM read_csv(
            {quoted_path},
            auto_detect=false,
            header=true,
            delim=',',
            quote='"',
            escape='"',
            columns={{{col_items}}},
            strict_mode=true,
            allow_quoted_nulls=false,
            max_line_size=8388608
        )
        """
        try:
            con.execute(view_sql)
            res = con.execute(f"SELECT count(*) FROM {view_name}").fetchall()
            count = int(res[0][0])
            inp.row_count = count
            row_counts[inp.name] = count
        except duckdb.Error as e:
            err_msg = str(e)
            line_match = re.search(r"line\s+(\d+)", err_msg, re.IGNORECASE)
            line_no = int(line_match.group(1)) if line_match else None
            # Find leading id from the line if possible, avoiding content leak
            leading_id = None
            if line_no and inp.path.exists():
                try:
                    with open(inp.path, "r", encoding="utf-8", errors="replace") as f:
                        for curr_line, line_text in enumerate(f, start=1):
                            if curr_line == line_no:
                                leading_id = line_text.split(",")[0].strip('" \r\n')[
                                    :64
                                ]
                                break
                except Exception:
                    pass

            raise InputError(
                code=ERR_CSV_MALFORMED,
                file=inp.name,
                line=line_no,
                record_id=leading_id,
                message=f"CSV parse error in '{inp.name}' at line {line_no or 'unknown'}",
            ) from None

    return row_counts
