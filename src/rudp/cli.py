"""CLI para protocolo RUDP."""
from __future__ import annotations
import argparse
import logging
import os
from pathlib import Path
from rudp.server import RUDPServer
from rudp.client import RUDPClient


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    p = argparse.ArgumentParser(prog="rudp", description="TF Redes: protocolo confiável sobre UDP")
    p.add_argument("-v", "--verbose", action="store_true", help="Logs detalhados")

    sub = p.add_subparsers(dest="cmd", required=True)

    # Servidor
    ps = sub.add_parser("server", help="Inicia o servidor")
    ps.add_argument("--bind", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=9000)
    ps.add_argument("--drop", type=float, default=0.0, help="Probabilidade de descarte [0..1]")

    # Cliente
    pc = sub.add_parser("client", help="Inicia o cliente")
    pc.add_argument("--host", default="127.0.0.1")
    pc.add_argument("--port", type=int, default=9000)
    pc.add_argument("--timeout", type=float, default=1.0)
    
    # Opções de dados (mutuamente exclusivas)
    data_group = pc.add_mutually_exclusive_group()
    data_group.add_argument("--message", "-m", default=None, help="Mensagem de texto para enviar")
    data_group.add_argument("--file", "-f", type=Path, help="Arquivo para enviar")
    data_group.add_argument("--synthetic", "-s", type=int, metavar="BYTES", 
                            help="Gerar dados sintéticos (N bytes)")

    args = p.parse_args()
    _setup_logging(args.verbose)
    log = logging.getLogger("rudp.cli")

    if args.cmd == "server":
        RUDPServer(bind=args.bind, port=args.port, drop_prob=args.drop).run()
    
    elif args.cmd == "client":
        client = RUDPClient(host=args.host, port=args.port, timeout_s=args.timeout)
        
        if not client.connect():
            log.error("Falha ao conectar")
            return
        
        # Determinar dados a enviar
        if args.file:
            if not args.file.exists():
                log.error("Arquivo não encontrado: %s", args.file)
                client.close()
                return
            data = args.file.read_bytes()
            log.info("Enviando arquivo: %s (%d bytes)", args.file, len(data))
        elif args.synthetic:
            data = os.urandom(args.synthetic)
            log.info("Enviando dados sintéticos: %d bytes", len(data))
        elif args.message:
            data = args.message.encode("utf-8")
        else:
            data = b"ola"  # Default
        
        stats = client.send_data(data)
        log.info("=== Resultado ===")
        log.info("  Pacotes: %d", stats.packets_sent)
        log.info("  Bytes: %d", stats.bytes_sent)
        log.info("  Tempo: %d ms", stats.time_ms)
        log.info("  Vazão: %.2f KB/s", stats.throughput_kbps)
        
        client.close()


if __name__ == "__main__":
    main()
