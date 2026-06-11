#!/usr/bin/env python3
"""
main.py — CLI entry point for subhunt.

Examples
--------
Basic scan (all sources, TXT output by default):
    python main.py -d example.com

All formats + verbose:
    python main.py -d example.com -f txt json csv -v

crt.sh only:
    python main.py -d example.com --disable-hackertarget --disable-rapiddns

Custom output directory and timeout:
    python main.py -d example.com --output-dir /tmp/results --timeout 60

After pip install (see setup.py):
    subhunt -d example.com -f json csv
"""

import argparse
import sys

from subhunt import __version__
from subhunt.logger import setup_logging
from subhunt.validator import validate_domain, validate_formats, VALID_FORMATS
from subhunt.scanner import run_scan, ScanConfig
from subhunt.display import (
    print_banner,
    print_info,
    print_success,
    print_error,
    print_results,
    print_summary,
    Spinner,
)
from subhunt.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subhunt",
        description=(
            "subhunt — Multi-source subdomain enumeration tool.\n"
            "Queries crt.sh, HackerTarget and RapidDNS, merges and deduplicates results.\n"
            "Designed for bug bounty hunters and OSINT practitioners."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  subhunt -d example.com
  subhunt -d example.com -f txt json csv -v
  subhunt -d example.com --disable-hackertarget --disable-rapiddns
  subhunt -d example.com --output-dir /tmp/out --timeout 60 --retries 5
  subhunt -d example.com -f json --no-file-log --no-banner
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

    # ── Sources ─────────────────────────────────────────────────────────────
    sources = parser.add_argument_group("sources")
    sources.add_argument(
        "--disable-hackertarget",
        action="store_true",
        help="Disable HackerTarget API (enabled by default)",
    )
    sources.add_argument(
        "--disable-rapiddns",
        action="store_true",
        help="Disable RapidDNS scraping (enabled by default)",
    )

    # ── Probing ─────────────────────────────────────────────────────────────
    probing = parser.add_argument_group("probing")
    probing.add_argument(
        "--probe",
        action="store_true",
        help="After enumeration, check which subdomains are alive (HTTP/HTTPS)",
    )
    probing.add_argument(
        "--probe-timeout",
        type=int,
        default=5,
        metavar="SEC",
        help="Timeout per probe request in seconds (default: 5)",
    )
    probing.add_argument(
        "--probe-workers",
        type=int,
        default=20,
        metavar="N",
        help="Parallel threads for probing (default: 20)",
    )
    probing.add_argument(
        "--alive-only",
        action="store_true",
        help="Only display/export alive subdomains (requires --probe)",
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

    # ── Build sources label ──────────────────────────────────────────────────
    active_sources = ["CRT.sh"]
    if not args.disable_hackertarget:
        active_sources.append("HackerTarget")
    if not args.disable_rapiddns:
        active_sources.append("RapidDNS")
    sources_label = " + ".join(active_sources)

    # ── Run scan ────────────────────────────────────────────────────────────
    config = ScanConfig(
        domain=domain,
        formats=formats,
        output_dir=args.output_dir,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
        use_hackertarget=not args.disable_hackertarget,
        use_rapiddns=not args.disable_rapiddns,
        probe=args.probe,
        probe_timeout=args.probe_timeout,
        probe_workers=args.probe_workers,
        alive_only=args.alive_only,
    )

    print_info(f"Target domain    : {domain}")
    print_info(f"Sources          : {sources_label}")
    print_info(f"Export formats   : {', '.join(formats) if formats else '(none)'}")
    print_info(f"Output directory : {args.output_dir}")
    print_info(f"Timeout / Retries: {args.timeout}s / {args.retries}")
    if args.probe:
        print_info(f"Probing : enabled ({args.probe_workers} workers, {args.probe_timeout}s timeout)")

    with Spinner(f"Enumerating subdomains for {domain}"):
        result = run_scan(config)

    # ── Output ──────────────────────────────────────────────────────────────
    if not result.success:
        print_error(f"Scan failed: {result.error}")
        return 1

    print_results(result.subdomains, domain, probe_results=result.probe_results or None)
    print_summary(
        domain=domain,
        total=len(result.subdomains),
        cert_count=result.cert_count,
        exported=result.exported_files,
        elapsed=result.elapsed,
        hackertarget_count=result.hackertarget_count,
        rapiddns_count=result.rapiddns_count,
        alive_count=result.alive_count,
        dead_count=result.dead_count,
    )

    if result.subdomains:
        print_success(f"Done. {len(result.subdomains)} unique subdomain(s) found for {domain}.")
        return 0
    else:
        print_error(f"No subdomains discovered for {domain}.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
