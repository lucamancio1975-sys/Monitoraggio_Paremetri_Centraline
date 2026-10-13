import logging
import time
import requests
from pathlib import Path
from src.config import CFR_HEADERS, DOWNLOAD_TIMEOUT, TEMP_DIR

logger = logging.getLogger("CFRCollector")

def scarica_immagine(url: str, dest_path: Path, max_tentativi: int = 3) -> bool:
    """
    Scarica l'immagine PNG del grafico dal server del CFR Toscana.
    Include meccanismo di retry esponenziale con attesa progressiva per proteggere da interruzioni di rete.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    for tentativo in range(1, max_tentativi + 1):
        try:
            response = requests.get(url, headers=CFR_HEADERS, timeout=DOWNLOAD_TIMEOUT)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Download completato: {dest_path.name} ({len(response.content)} bytes)")
                return True
            else:
                logger.warning(
                    f"Tentativo {tentativo}/{max_tentativi} fallito per {url} "
                    f"(HTTP {response.status_code}, dim: {len(response.content)})"
                )
        except Exception as e:
            logger.warning(f"Errore download tentativo {tentativo}/{max_tentativi}: {e}")

        if tentativo < max_tentativi:
            pausa = tentativo * 2
            logger.info(f"Attesa di {pausa}s prima del nuovo tentativo di download...")
            time.sleep(pausa)

    return False

def pulisci_cartella_temp(cartella: Path = TEMP_DIR):
    """Rimuove tutti i file scaricati nella cartella temporanea."""
    if not cartella.exists():
        return
    for item in cartella.iterdir():
        if item.is_file():
            try:
                item.unlink()
            except Exception as e:
                logger.debug(f"Impossibile rimuovere {item}: {e}")
