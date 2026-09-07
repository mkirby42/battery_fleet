import sys

from battery_fleet import serve


def run(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    if list(argv) != ["serve"]:
        print("usage: python -m battery_fleet serve", file=sys.stderr)
        raise SystemExit(2)
    serve.main()


if __name__ == "__main__":
    run()
