from __future__ import annotations

import argparse
from wsgiref.simple_server import make_server

from cars_returns.app import create_app
from cars_returns.db import initialize_database, seed_demo_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CARS returns MVP app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db-path", default="var/cars_returns.db")
    parser.add_argument("--init-db", action="store_true")
    args = parser.parse_args()

    initialize_database(args.db_path)
    seed_demo_data(args.db_path)
    if args.init_db:
        print(f"Initialized database at {args.db_path}")
        return

    app = create_app(db_path=args.db_path)
    with make_server(args.host, args.port, app) as server:
        print(f"Serving CARS returns app on http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
