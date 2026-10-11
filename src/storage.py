import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from src.config import DATA_DIR, DATA_STAZIONI_DIR

logger = logging.getLogger("CFRCollector")

CSV_COLUMNS = [
    "timestamp",
    "data",
    "ora",
    "fuso_orario",
    "stazione",
    "id_stazione",
    "temperatura_c",
    "umidita_rh",
    "stato_rilevamento",
]

def aggiorna_archivio_stazione(
    station_meta: Dict[str, str],
    nuovi_records: List[Dict[str, Any]],
) -> int:
    """
    Aggiorna i file CSV e JSON dedicati per la singola stazione in modalità idempotente.
    Se un record con lo stesso timestamp esiste già, viene sovrascritto con il valore aggiornato.
    Restituisce il numero totale di record archiviati per la stazione.
    """
    slug = station_meta["slug"]
    nome = station_meta["nome"]
    st_id = station_meta["id"]

    csv_path = DATA_STAZIONI_DIR / f"{slug}.csv"
    json_path = DATA_STAZIONI_DIR / f"{slug}.json"

    # Preparazione dizionario con chiave timestamp per merge
    database_records: Dict[str, Dict[str, Any]] = {}

    # 1. Carica dati preesistenti da JSON se presente (o da CSV)
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dati_esistenti = json.load(f)
                for rec in dati_esistenti.get("rilevamenti", []):
                    ts = rec.get("timestamp")
                    if ts:
                        database_records[ts] = rec
        except Exception as e:
            logger.warning(f"Errore lettura {json_path}: {e}")
    elif csv_path.exists():
        try:
            df_old = pd.read_csv(csv_path)
            for _, row in df_old.iterrows():
                rec = row.to_dict()
                ts = str(rec.get("timestamp"))
                database_records[ts] = rec
        except Exception as e:
            logger.warning(f"Errore lettura {csv_path}: {e}")

    # 2. Inserimento/Aggiornamento nuovi record
    for r in nuovi_records:
        rec_completo = {
            "timestamp": r["timestamp"],
            "data": r["data"],
            "ora": r["ora"],
            "fuso_orario": r["fuso_orario"],
            "stazione": nome,
            "id_stazione": st_id,
            "temperatura_c": r["temperatura_c"],
            "umidita_rh": r["umidita_rh"],
            "stato_rilevamento": r["stato_rilevamento"],
        }
        database_records[r["timestamp"]] = rec_completo

    # 3. Ordinamento cronologico
    records_ordinati = [
        database_records[k] for k in sorted(database_records.keys())
    ]

    # 4. Salvataggio JSON stazione
    payload_json = {
        "stazione": nome,
        "id_stazione": st_id,
        "totale_rilevamenti": len(records_ordinati),
        "ultimo_aggiornamento": records_ordinati[-1]["timestamp"] if records_ordinati else None,
        "rilevamenti": records_ordinati,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload_json, f, indent=2, ensure_ascii=False)

    # 5. Salvataggio CSV stazione
    df = pd.DataFrame(records_ordinati)
    if not df.empty:
        # Assicura ordine coerente delle colonne
        colonne_presenti = [c for c in CSV_COLUMNS if c in df.columns]
        df = df[colonne_presenti]
        df.to_csv(csv_path, index=False, encoding="utf-8")

    logger.info(f"[{nome}] Aggiornati file {slug}.csv e {slug}.json ({len(records_ordinati)} record totali)")
    return len(records_ordinati)


def aggiorna_archivio_cumulativo(tutti_i_records: List[Dict[str, Any]]):
    """
    Aggiorna anche i file master complessivi 'dati/archivio_completo.csv' e '.json'.
    Questo fornisce un unico punto di accesso rapido per tutte le 11 stazioni.
    """
    master_csv = DATA_DIR / "archivio_completo.csv"
    master_json = DATA_DIR / "archivio_completo.json"

    mappa_master: Dict[str, Dict[str, Any]] = {}

    if master_csv.exists():
        try:
            df_old = pd.read_csv(master_csv)
            for _, row in df_old.iterrows():
                rec = row.to_dict()
                chiave = f"{rec.get('id_stazione')}_{rec.get('timestamp')}"
                mappa_master[chiave] = rec
        except Exception as e:
            logger.warning(f"Errore lettura master CSV: {e}")

    for r in tutti_i_records:
        chiave = f"{r['id_stazione']}_{r['timestamp']}"
        mappa_master[chiave] = r

    lista_ordinata = sorted(
        mappa_master.values(),
        key=lambda x: (str(x.get("timestamp")), str(x.get("stazione"))),
    )

    if lista_ordinata:
        df_master = pd.DataFrame(lista_ordinata)
        colonne_presenti = [c for c in CSV_COLUMNS if c in df_master.columns]
        df_master = df_master[colonne_presenti]
        df_master.to_csv(master_csv, index=False, encoding="utf-8")

        payload_json = {
            "totale_rilevamenti": len(lista_ordinata),
            "rilevamenti": lista_ordinata,
        }
        with open(master_json, "w", encoding="utf-8") as f:
            json.dump(payload_json, f, indent=2, ensure_ascii=False)

        logger.info(f"Master database aggiornato ({len(lista_ordinata)} record complessivi)")
