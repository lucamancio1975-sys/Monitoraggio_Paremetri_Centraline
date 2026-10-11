import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
import pytz

from src.config import (
    STAZIONI_FILE,
    TEMP_DIR,
    TIMEZONE_ITALIA,
)
from src.downloader import scarica_immagine, pulisci_cartella_temp
from src.cv_engine import analizza_stazione_giornaliera
from src.storage import aggiorna_archivio_stazione, aggiorna_archivio_cumulativo

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("CFRCollector")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collettore automatico dati meteo CFR Toscana (Termometria e Igrometria)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Data target nel formato YYYY-MM-DD. Se non specificata, usa la data corrente di Roma.",
    )
    parser.add_argument(
        "--cron-guard",
        action="store_true",
        help="Se attivo, verifica che l'ora locale italiana sia effettivamente quella di chiusura (dalle 23:00 in poi). Evita doppie esecuzioni dovute al doppio cron UTC per ora solare/legale.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    rome_tz = pytz.timezone(TIMEZONE_ITALIA)
    now_rome = datetime.now(rome_tz)

    logger.info("=" * 65)
    logger.info("AVVIO MONITORAGGIO PARAMETRI AMBIENTALI CFR TOSCANA")
    logger.info(f"Ora locale Roma: {now_rome.strftime('%Y-%m-%d %H:%M:%S %Z')} (Offset: {now_rome.strftime('%z')})")

    # Verifica cron-guard per gestione automatica ora solare (CET) vs legale (CEST)
    if args.cron_guard:
        if now_rome.hour < 23:
            logger.info(
                f"Controllo orario attivo: a Roma sono le {now_rome.strftime('%H:%M')} ({now_rome.tzname()}). "
                "L'elaborazione deve avvenire alle 23:50. Uscita senza elaborazione."
            )
            sys.exit(0)

    # Determinazione data di analisi
    if args.data:
        try:
            target_date = datetime.strptime(args.data, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Formato data non valido: {args.data}. Usare YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = now_rome.date()

    logger.info(f"Data di analisi: {target_date.strftime('%Y-%m-%d')}")

    # Caricamento elenco stazioni
    if not STAZIONI_FILE.exists():
        logger.error(f"File di configurazione non trovato: {STAZIONI_FILE}")
        sys.exit(1)

    with open(STAZIONI_FILE, "r", encoding="utf-8") as f:
        stazioni = json.load(f)

    logger.info(f"Caricate {len(stazioni)} stazioni meteo da monitorare.")

    tutti_i_records_cumulativi = []
    stazioni_successo = 0
    stazioni_fallite = 0

    for idx, staz in enumerate(stazioni, 1):
        slug = staz["slug"]
        nome = staz["nome"]
        logger.info(f"[{idx}/{len(stazioni)}] Elaborazione stazione: {nome} ({staz['id']})...")

        termo_path = TEMP_DIR / f"{slug}_termo_{target_date}.png"
        igro_path = TEMP_DIR / f"{slug}_igro_{target_date}.png"

        # 1. Download dei grafici
        ok_termo = scarica_immagine(staz["url_termo"], termo_path)
        ok_igro = scarica_immagine(staz["url_igro"], igro_path)

        if not ok_termo or not ok_igro:
            logger.error(f"Impossibile scaricare entrambi i grafici per {nome}. Stazione saltata.")
            stazioni_fallite += 1
            continue

        # 2. Analisi Computer Vision (OpenCV)
        try:
            records = analizza_stazione_giornaliera(
                file_termo_path=termo_path,
                file_igro_path=igro_path,
                data_riferimento=target_date,
                rome_tz=rome_tz,
            )

            # 3. Archiviazione file stazione dedicati (CSV e JSON)
            aggiorna_archivio_stazione(staz, records)

            # Accumulo per master
            for r in records:
                r_master = dict(r)
                r_master["stazione"] = nome
                r_master["id_stazione"] = staz["id"]
                tutti_i_records_cumulativi.append(r_master)

            stazioni_successo += 1

        except Exception as e:
            logger.exception(f"Errore durante l'analisi Computer Vision per {nome}: {e}")
            stazioni_fallite += 1

    # 4. Aggiornamento archivio complessivo
    if tutti_i_records_cumulativi:
        aggiorna_archivio_cumulativo(tutti_i_records_cumulativi)

    # 5. Pulizia cartella scarichi temporanei
    pulisci_cartella_temp(TEMP_DIR)
    logger.info("File temporanei PNG rimossi con successo.")

    logger.info("=" * 65)
    logger.info(f"RIEPILOGO FINALE: {stazioni_successo}/{len(stazioni)} stazioni elaborate con successo.")
    if stazioni_fallite > 0:
        logger.warning(f"Attenzione: {stazioni_fallite} stazioni non elaborate per errori di rete o parsing.")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
