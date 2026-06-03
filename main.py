#!/usr/bin/env python3
"""
main.py — CLI entry point for crtsh-recon.

Examples
--------
Basic scan (TXT output by default):
    python main.py -d example.com

All formats + verbose:
    python main.py -d example.com -f txt json csv -v

Custom output directory and timeout:
    python main.py -d example.com --output-dir /tmp/results --timeout 60

After pip install (see setup.py):
    crtsh-recon -d example.com -f json csv
"""

import argparse
import sys

from crtsh_recon import __version__
from crtsh_recon.logger import setup_logging
from crtsh_recon.validator import validate_domain, validate_formats, VALID_FORMATS
from crtsh_recon.scanner import run_scan, ScanConfig
from crtsh_recon.display import (
    print_banner,
    print_info,
    print_success,
    print_error,
    print_results,
    print_summary,
    Spinner,
)
from crtsh_recon.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crtsh-recon",
        description=(
            "crtsh-recon — Subdomain enumeration via crt.sh Certificate Transparency logs.\n"
            "Designed for bug bounty hunters and OSINT practitioners."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  crtsh-recon -d example.com
  crtsh-recon -d example.com -f txt json csv -v
  crtsh-recon -d example.com --output-dir /tmp/out --timeout 60 --retries 5
  crtsh-recon -d example.com -f json --no-file-log
        """,
    )

    # ── Target ──────────────────────────────────────────────────────────────
    target = parser.add_argument_group("target")
    target.add_argument(
        "-d",
        "--domain",
        required=True,
        metavar="DOMAIN",
        help="Apex domain to enumerate (e.g. example.com)",
    )

    # ── Output ──────────────────────────────────────────────────────────────
    output = parser.add_argument_group("output")
    output.add_argument(
        "-f",
        "--formats",
        nargs="+",
        default=["txt"],
        metavar="FORMAT",
        choices=list(VALID_FORMATS),
        help=f"Export format(s). Choices: {', '.join(sorted(VALID_FORMATS))}. Default: txt",
    )
    output.add_argument(
        "-o",
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory for exported result files (default: ./output)",
    )
    output.add_argument(
        "--no-export",
        action="store_true",
        help="Skip file export; print results only",
    )

    # ── Network ─────────────────────────────────────────────────────────────
    network = parser.add_argument_group("network")
    network.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SEC",
        help="HTTP request timeout in seconds (default: 30)",
    )
    network.add_argument(
        "--retries",
        type=int,
        default=3,
        metavar="N",
        help="Number of retry attempts on failure (default: 3)",
    )
    network.add_argument(
        "--backoff",
        type=float,
        default=2.0,
        metavar="FACTOR",
        help="Exponential back-off factor between retries (default: 2.0)",
    )

    # ── Logging ─────────────────────────────────────────────────────────────
    logging_group = parser.add_argument_group("logging")
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level console output",
    )
    logging_group.add_argument(
        "--log-dir",
        default="logs",
        metavar="DIR",
        help="Directory for rotating log files (default: ./logs)",
    )
    logging_group.add_argument(
        "--no-file-log",
        action="store_true",
        help="Disable file logging entirely",
    )

    # ── Misc ────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the ASCII art banner (useful for scripting)",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """
    CLI entry-point.

    Returns:
        Exit code: 0 on success, 1 on error, 2 on validation failure.
    """
    parser = build_parser()
    args = parser.parse_args()

    # ── Logging setup ───────────────────────────────────────────────────────
    setup_logging(
        verbose=args.verbose,
        log_dir=args.log_dir,
        log_to_file=not args.no_file_log,
    )

    # ── Banner ──────────────────────────────────────────────────────────────
    if not args.no_banner:
        print_banner(__version__)

    # ── Validate inputs ─────────────────────────────────────────────────────
    try:
        domain = validate_domain(args.domain)
        formats = [] if args.no_export else validate_formats(args.formats)
    except ValidationError as exc:
        print_error(str(exc))
        return 2

    # ── Run scan ────────────────────────────────────────────────────────────
    config = ScanConfig(
        domain=domain,
        formats=formats,
        output_dir=args.output_dir,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
    )

    print_info(f"Target domain   : {domain}")
    print_info(f"Export formats  : {', '.join(formats) if formats else '(none)'}")
    print_info(f"Output directory: {args.output_dir}")
    print_info(f"Timeout / Retries: {args.timeout}s / {args.retries}")

    with Spinner(f"Querying crt.sh for *.{domain}"):
        result = run_scan(config)

    # ── Output ──────────────────────────────────────────────────────────────
    if not result.success:
        print_error(f"Scan failed: {result.error}")
        return 1

    print_results(result.subdomains, domain)
    print_summary(
        domain=domain,
        total=len(result.subdomains),
        cert_count=result.cert_count,
        exported=result.exported_files,
        elapsed=result.elapsed,
    )

    if result.subdomains:
        print_success(
            f"Done. {len(result.subdomains)} unique subdomain(s) found for {domain}."
        )
    else:
        print_error(f"No subdomains discovered for {domain}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
