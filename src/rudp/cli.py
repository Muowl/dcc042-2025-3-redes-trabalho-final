from __future__ import annotations
import argparse
import logging
from rudp.server import RUDPServer
from rudp.client import RUDPClient

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

def main() -> None:
    p = argparse.ArgumentParser(prog="rudp", description="TF Redes: protocolo confiável sobre UDP")
    p.add_argument("-v", "--verbose", action="store_true", help="Logs detalhados")

    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("server", help="Inicia o servidor")
    ps.add_argument("--bind", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=9000)
    ps.add_argument("--drop", type=float, default=0.0, help="Probabilidade de descarte [0..1]")

    pc = sub.add_parser("client", help="Inicia o cliente")
    pc.add_argument("--host", default="127.0.0.1")
    pc.add_argument("--port", type=int, default=9000)
    pc.add_argument("--message", default="ola")
    pc.add_argument("--timeout", type=float, default=1.0)

    args = p.parse_args()
    _setup_logging(args.verbose)

    if args.cmd == "server":
        RUDPServer(bind=args.bind, port=args.port, drop_prob=args.drop).run()
    elif args.cmd == "client":
        RUDPClient(host=args.host, port=args.port, timeout_s=args.timeout).send_message(args.message)

if __name__ == "__main__":
    main()
