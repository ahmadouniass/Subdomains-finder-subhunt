"""
display.py — Terminal output helpers: banners, progress, result tables.

Falls back gracefully when colorama is not installed.
"""

import sys
import logging
from typing import Optional

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _COLOR_AVAILABLE = True
except ImportError:
    _COLOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _c(text: str, color_code: str) -> str:
    """Wrap *text* in an ANSI color code if colorama is available."""
    if _COLOR_AVAILABLE:
        return f"{color_code}{text}{Style.RESET_ALL}"
    return text


def green(text: str) -> str:
    return _c(text, Fore.GREEN) if _COLOR_AVAILABLE else text


def cyan(text: str) -> str:
    return _c(text, Fore.CYAN) if _COLOR_AVAILABLE else text


def yellow(text: str) -> str:
    return _c(text, Fore.YELLOW) if _COLOR_AVAILABLE else text


def red(text: str) -> str:
    return _c(text, Fore.RED) if _COLOR_AVAILABLE else text


def bold(text: str) -> str:
    if _COLOR_AVAILABLE:
        return f"{Style.BRIGHT}{text}{Style.RESET_ALL}"
    return text


def dim(text: str) -> str:
    if _COLOR_AVAILABLE:
        return f"{Style.DIM}{text}{Style.RESET_ALL}"
    return text


# ---------------------------------------------------------------------------
# Banner & section headers
# ---------------------------------------------------------------------------

BANNER = r"""
  ███████╗██╗   ██╗██████╗ ██╗  ██╗██╗   ██╗███╗   ██╗████████╗
  ██╔════╝██║   ██║██╔══██╗██║  ██║██║   ██║████╗  ██║╚══██╔══╝
  ███████╗██║   ██║██████╔╝███████║██║   ██║██╔██╗ ██║   ██║
  ╚════██║██║   ██║██╔══██╗██╔══██║██║   ██║██║╚██╗██║   ██║
  ███████║╚██████╔╝██████╔╝██║  ██║╚██████╔╝██║ ╚████║   ██║
  ╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝
"""
_SHORT_BANNER = "  subhunt - Subdomain Enumeration via Certificate Transparency logs & HackerTarget"


def print_banner(version: str = "1.0.0") -> None:
    """Print the ASCII art banner to stdout."""
    try:
        print(cyan(BANNER))
    except UnicodeEncodeError:
        print(cyan(_SHORT_BANNER))
    print(dim(f"  v{version}   CRT SH |  https://github.com/ahmadouniass/Subdomains-finder-crtsh"))
    print()


def print_section(title: str) -> None:
    """Print a styled section separator."""
    line = "─" * 60
    print(f"\n{bold(cyan(line))}")
    print(f"  {bold(title)}")
    print(f"{bold(cyan(line))}")


def print_info(message: str) -> None:
    print(f"  {cyan('[*]')} {message}")


def print_success(message: str) -> None:
    print(f"  {green('[+]')} {message}")


def print_warning(message: str) -> None:
    print(f"  {yellow('[!]')} {message}", file=sys.stderr)


def print_error(message: str) -> None:
    print(f"  {red('[✗]')} {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Subdomain result table
# ---------------------------------------------------------------------------


def print_results(subdomains: list[str], domain: str) -> None:
    """
    Render a clean, numbered list of discovered subdomains.

    Args:
        subdomains: Sorted list of subdomain strings.
        domain:     Apex domain (displayed in the section header).
    """
    print_section(f"Results for {bold(domain)}")

    if not subdomains:
        print_warning("No subdomains discovered.")
        return

    width = len(str(len(subdomains)))  # dynamic index column width
    for idx, sub in enumerate(subdomains, start=1):
        index_col = dim(f"  {idx:>{width}}.")
        # Highlight the apex part of the subdomain differently
        if sub == domain:
            subdomain_col = yellow(sub)
        else:
            prefix = sub[: len(sub) - len(domain) - 1]
            apex = sub[len(sub) - len(domain) :]
            subdomain_col = green(prefix) + dim(f".{apex}")
        print(f"{index_col}  {subdomain_col}")

    print()


def print_summary(
    domain: str,
    total: int,
    cert_count: int,
    exported: dict,
    elapsed: float,
    hackertarget_count: int = 0,
    rapiddns_count: int = 0,
) -> None:
    """
    Print a final summary block.

    Args:
        domain:             Apex domain.
        total:              Total unique subdomains found.
        cert_count:         Number of raw cert records fetched.
        exported:           Mapping of format → file path.
        elapsed:            Wall-clock seconds for the full run.
        hackertarget_count: Number of subdomains found via HackerTarget.
        rapiddns_count:     Number of subdomains found via RapidDNS.
    """
    print_section("Summary")
    print_info(f"Domain           : {bold(domain)}")
    print_info(f"Cert records     : {bold(str(cert_count))}")
    if hackertarget_count > 0:
        print_info(f"HackerTarget     : {bold(str(hackertarget_count))}")
    if rapiddns_count > 0:
        print_info(f"RapidDNS         : {bold(str(rapiddns_count))}")
    print_info(f"Unique subdomains: {bold(green(str(total)))}")
    print_info(f"Elapsed time     : {bold(f'{elapsed:.2f}s')}")

    if exported:
        print()
        print_info("Exported files:")
        for fmt, path in exported.items():
            print(f"       {dim(fmt.upper() + ':')}  {cyan(str(path))}")

    print()


# ---------------------------------------------------------------------------
# Spinner / progress
# ---------------------------------------------------------------------------


class Spinner:
    """
    A simple TTY spinner for use around blocking I/O.

    Usage::

        with Spinner("Querying crt.sh"):
            data = client.fetch_certificates(domain)
    """

    _FRAMES = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]

    def __init__(self, message: str = "Working") -> None:
        self.message = message
        self._thread: Optional[object] = None
        self._stop_event: Optional[object] = None
        self._is_tty = sys.stdout.isatty()

    def __enter__(self) -> "Spinner":
        if not self._is_tty:
            print_info(self.message + " …")
            return self
        import threading

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, *_) -> None:
        if not self._is_tty:
            return
        if self._stop_event:
            self._stop_event.set()
        if self._thread:
            self._thread.join()
        # Clear spinner line
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()

    def _spin(self) -> None:
        import time

        frame_idx = 0
        while not self._stop_event.is_set():
            frame = self._FRAMES[frame_idx % len(self._FRAMES)]
            sys.stdout.write(f"\r  {cyan(frame)}  {self.message} ")
            sys.stdout.flush()
            frame_idx += 1
            time.sleep(0.1)
