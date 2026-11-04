"""CLI entry points for aimx-recipes."""

import argparse
import os
import sys
from typing import Any, Sequence
import duckdb
from aimx_recipes.cli.output import (
    ERR_USAGE_ERROR,
    ERR_WRITE_FAILED,
    build_envelope,
    now_utc_iso,
    render_json,
    render_text,
)


class CLIError(Exception):
    """Raised for CLI argument parsing errors."""

    def __init__(self, message: str, code: str = ERR_USAGE_ERROR):
        super().__init__(message)
        self.message = message
        self.code = code


class StrictArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises CLIError instead of exiting."""

    def error(self, message: str):
        raise CLIError(message)


def create_parser() -> StrictArgumentParser:
    parser = StrictArgumentParser(
        prog="aimx-recipes",
        description="Core schemas, facet vocabulary, and offline contract validation for aimx recipes",
        exit_on_error=False,
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    ingest_parser = subparsers.add_parser("ingest", exit_on_error=False)
    ingest_sub = ingest_parser.add_subparsers(dest="source", required=True)

    kaggle_parser = ingest_sub.add_parser("kaggle", exit_on_error=False)
    kaggle_parser.add_argument(
        "--meta-kaggle", required=True, help="Directory containing Meta Kaggle CSVs"
    )
    kaggle_parser.add_argument(
        "--data-dir", default="data", help="Output data directory (default: data)"
    )
    kaggle_parser.add_argument(
        "--label", default=None, help="Label recorded in manifest"
    )
    kaggle_parser.add_argument(
        "--threads",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="Number of threads for processing",
    )
    kaggle_parser.add_argument(
        "--memory-limit", default="4GB", help="DuckDB memory limit (default: 4GB)"
    )
    kaggle_parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON envelope"
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point returning exit code (0, 1, 2). Never calls sys.exit."""
    if argv is None:
        argv = sys.argv[1:]

    is_json = "--json" in argv
    started_at = now_utc_iso()
    cmd_name = (
        "ingest kaggle"
        if len(argv) >= 2 and argv[0] == "ingest" and argv[1] == "kaggle"
        else "aimx-recipes"
    )

    parser = create_parser()
    try:
        args = parser.parse_args(argv)
    except CLIError as e:
        if is_json:
            envelope = build_envelope(
                command=cmd_name,
                status="error",
                run_started_at=started_at,
                errors=[{"code": e.code, "message": e.message}],
            )
            sys.stdout.write(render_json(envelope) + "\n")
        else:
            sys.stderr.write(f"usage error: {e.message}\n")
        return 2
    except Exception as e:
        if is_json:
            envelope = build_envelope(
                command=cmd_name,
                status="error",
                run_started_at=started_at,
                errors=[{"code": ERR_USAGE_ERROR, "message": str(e)}],
            )
            sys.stdout.write(render_json(envelope) + "\n")
        else:
            sys.stderr.write(f"error: {e}\n")
        return 2

    if args.subcommand == "ingest" and args.source == "kaggle":
        try:
            import aimx_recipes.sources.kaggle as kaggle_mod

            result = kaggle_mod.ingest(
                meta_kaggle=args.meta_kaggle,
                data_dir=args.data_dir,
                label=args.label,
                threads=args.threads,
                memory_limit=args.memory_limit,
            )
            # When fully implemented, result provides envelope data
            envelope = result.to_envelope(run_started_at=started_at)
            exit_code = 0 if envelope.get("status") == "ok" else 1
        except (OSError, duckdb.IOException):
            envelope = build_envelope(
                command="ingest kaggle",
                status="error",
                run_started_at=started_at,
                errors=[
                    {
                        "code": ERR_WRITE_FAILED,
                        "message": "File operation or disk write failed",
                    }
                ],
            )
            exit_code = 1
        except NotImplementedError as e:
            envelope = build_envelope(
                command="ingest kaggle",
                status="error",
                run_started_at=started_at,
                errors=[
                    {
                        "code": "not_implemented",
                        "message": f"Kaggle ingest not implemented: {e}",
                    }
                ],
            )
            exit_code = 1
        except Exception as e:
            code = getattr(e, "code", "runtime_error")
            raw_msg = str(e)
            if code == "runtime_error":
                clean_msg = "An unexpected runtime error occurred during ingestion"
            else:
                clean_msg = raw_msg
            err_dict: dict[str, Any] = {"code": code, "message": clean_msg}
            if getattr(e, "file", None):
                err_dict["file"] = e.file
            if getattr(e, "line", None) is not None:
                err_dict["line"] = e.line
            if getattr(e, "record_id", None):
                err_dict["record_id"] = e.record_id
            if getattr(e, "column", None):
                err_dict["column"] = e.column

            errs = [err_dict]
            if getattr(e, "diagnostics", None):
                errs.extend(e.diagnostics)

            envelope = build_envelope(
                command="ingest kaggle",
                status="error",
                run_started_at=started_at,
                errors=errs,
            )
            exit_code = 1

        if args.json:
            sys.stdout.write(render_json(envelope) + "\n")
        else:
            text = render_text(envelope)
            if text:
                sys.stdout.write(text + "\n")
            if exit_code != 0 and envelope.get("errors"):
                # Write errors to stderr as well
                for err in envelope["errors"]:
                    sys.stderr.write(
                        f"error: [{err.get('code')}] {err.get('message')}\n"
                    )
        return exit_code

    return 0
