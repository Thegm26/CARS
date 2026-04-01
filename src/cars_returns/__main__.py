from __future__ import annotations

from wsgiref.simple_server import make_server

from cars_returns.app import create_app


def main() -> None:
    app = create_app()
    with make_server("127.0.0.1", 8000, app) as server:
        print("Serving CARS returns app on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    main()

