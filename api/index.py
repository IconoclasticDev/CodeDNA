"""Vercel serverless entry point for the CodeDNA API and static UI."""

from urllib.parse import parse_qs, urlsplit

from codedna.server import Handler


class handler(Handler):
    """Restore the public route after Vercel's internal rewrite."""

    def _restore_path(self) -> None:
        parsed = urlsplit(self.path)
        route = parse_qs(parsed.query).get("__route", [None])[0]
        if route is not None:
            self.path = "/" if route == "root" else f"/{route.lstrip('/')}"

    def do_GET(self) -> None:
        self._restore_path()
        super().do_GET()

    def do_POST(self) -> None:
        self._restore_path()
        super().do_POST()
