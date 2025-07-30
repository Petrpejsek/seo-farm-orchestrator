#!/usr/bin/env python3
"""
SEO Farm Orchestrator CLI

Usage:
  seo-farm run --topic "Your topic"
  seo-farm run --csv input/topics.csv  
  seo-farm worker
  seo-farm --help
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# Nastavenie cesty k current working directory pre importy
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Kontrola či sme v správnom adresári
if not (project_root / "activities").exists():
    print("❌ SEO Farm Orchestrator musí byť spustený z project root adresára")
    print(f"   Aktuálny adresár: {os.getcwd()}")
    print(f"   Project root: {project_root}")
    print("   Použite: cd /path/to/seo-farm-orchestrator")
    sys.exit(1)

try:
    from scripts.test_cli import process_single_topic, process_csv_topics
    from worker import main as worker_main
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Uistite sa, že ste v správnom adresári a všetky dependencies sú nainštalované")
    print("   Spustite: pip install -r requirements.txt")
    sys.exit(1)

def run_command(args):
    """Spustí SEO pipeline"""
    if args.csv:
        print(f"🚀 Spúšťam bulk processing z CSV: {args.csv}")
        asyncio.run(process_csv_topics(args.csv))
    elif args.topic:
        print(f"🚀 Spracovávam jedno téma: {args.topic}")
        asyncio.run(process_single_topic(args.topic))
    else:
        print("❌ Musíte zadať buď --topic alebo --csv")
        sys.exit(1)

def worker_command(args):
    """Spustí Temporal worker"""
    print("🔄 Spúšťam Temporal worker...")
    asyncio.run(worker_main())

def main():
    """Hlavná CLI funkcia"""
    
    parser = argparse.ArgumentParser(
        prog="seo-farm",
        description="🎯 SEO Farm Orchestrator - AI-powered SEO content generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Príklady použitia:
  seo-farm run --topic "AI nástroje pre marketing"
  seo-farm run --csv input/topics.csv
  seo-farm worker

Environment premenné:
  OPENAI_API_KEY      - OpenAI API kľúč (povinné)
  OPENAI_ASSISTANT_ID - OpenAI Assistant ID (povinné)
  SAVE_TO_DB          - Ukladanie do databázy (voliteľné, default: false)
  DATABASE_URL        - PostgreSQL connection string (voliteľné)
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Dostupné príkazy")
    
    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Spustí SEO content generation")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--topic", "-t", type=str, help="Jednotlivé téma pre spracovanie")
    run_group.add_argument("--csv", "-c", type=str, help="CSV súbor s témami")
    
    # Worker subcommand  
    worker_parser = subparsers.add_parser("worker", help="Spustí Temporal worker")
    
    # Version subcommand
    version_parser = subparsers.add_parser("version", help="Zobrazí verziu")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "run":
        run_command(args)
    elif args.command == "worker":
        worker_command(args)
    elif args.command == "version":
        from . import __version__
        print(f"SEO Farm Orchestrator v{__version__}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 