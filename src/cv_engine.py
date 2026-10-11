import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz

from src.config import (
    Y_0,
    Y_MAX,
    DY,
    VALORE_MAX_RH,
    MAPPA_ORE_OGGI,
    TOLLERANZA_GRIGIO_LINEA,
    TOLLERANZA_GRIGIO_COLONNA,
    HSV_LOWER_BLUE,
    HSV_UPPER_BLUE,
)

logger = logging.getLogger("CFRCollector")

def rileva_valore_massimo_temperatura(img_path: Path) -> float:
    """
    Rileva automaticamente il valore massimo della scala della temperatura
    contando le linee grigie orizzontali interne della griglia (colore 192, 192, 192).
    Ogni intervallo tra le linee corrisponde esattamente a 2.0 °C.
    """
    img = cv2.imread(str(img_path))
    if img is None:
        logger.warning(f"Impossibile aprire {img_path}. Uso fallback scala T=34.0°C")
        return 34.0

    x = 200  # Colonna interna alla griglia, esente da etichette o bordi
    linee_grigie = 0
    in_linea = False

    # Scansione dell'intervallo verticale escludendo i bordi esterni
    for y in range(55, 370):
        b, g, r = img[y, x]
        # Grigio griglia CFR Toscana standard: [192, 192, 192]
        if (
            abs(int(b) - 192) < TOLLERANZA_GRIGIO_LINEA
            and abs(int(g) - 192) < TOLLERANZA_GRIGIO_LINEA
            and abs(int(r) - 192) < TOLLERANZA_GRIGIO_LINEA
        ):
            if not in_linea:
                linee_grigie += 1
                in_linea = True
        else:
            in_linea = False

    if linee_grigie > 0:
        val_max = float((linee_grigie + 1) * 2.0)
        logger.debug(f"{img_path.name}: rilevate {linee_grigie} linee grigie -> Scala max T: {val_max}°C")
        return val_max

    return 34.0  # Fallback standard estivo/autunnale


def trova_pixel_blu_in_colonna(img_path: Path, x_target: int, max_offset: int = 4) -> Optional[int]:
    """
    Rileva con precisione sub-pixel la coordinata Y della curva blu per l'ora target.
    1. Allineamento dinamico della coordinata X sulla linea verticale della griglia.
    2. Tolleranza HSV estesa per gestire le intersezioni tra curva e griglia.
    3. Calcolo del centroide verticale lungo lo spessore della linea.
    """
    img = cv2.imread(str(img_path))
    if img is None:
        return None

    # 1. Allineamento dinamico sulla linea verticale della griglia
    x_allineata = x_target
    max_grigi = 0
    for x_test in range(max(0, x_target - 4), min(img.shape[1], x_target + 5)):
        grigi = 0
        for y_test in range(Y_MAX + 5, Y_0 - 5):
            b, g, r = img[y_test, x_test]
            if (
                abs(int(b) - 192) < TOLLERANZA_GRIGIO_COLONNA
                and abs(int(g) - 192) < TOLLERANZA_GRIGIO_COLONNA
                and abs(int(r) - 192) < TOLLERANZA_GRIGIO_COLONNA
            ):
                grigi += 1
        if grigi > max_grigi:
            max_grigi = grigi
            x_allineata = x_test

    if max_grigi < 30:
        x_allineata = x_target

    # 2. Mascheratura HSV per il colore blu della traccia dati
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_blue = np.array(HSV_LOWER_BLUE)
    upper_blue = np.array(HSV_UPPER_BLUE)
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Funzione per determinare il centroide verticale
    def get_centroid(col_x: int) -> Optional[int]:
        y_pixels = []
        for y in range(Y_MAX, Y_0 + 1):
            if mask[y, col_x] == 255:
                y_pixels.append(y)
        if y_pixels:
            return int(round(float(np.mean(y_pixels))))
        return None

    # 3. Centroide sulla colonna allineata
    y_centroid = get_centroid(x_allineata)
    if y_centroid is not None:
        return y_centroid

    # Fallback orizzontale in caso di micro-interruzione locale
    for offset in range(1, max_offset + 1):
        for adj_x in [x_allineata - offset, x_allineata + offset]:
            if 0 <= adj_x < mask.shape[1]:
                y_centroid = get_centroid(adj_x)
                if y_centroid is not None:
                    return y_centroid

    return None


def analizza_stazione_giornaliera(
    file_termo_path: Path,
    file_igro_path: Path,
    data_riferimento: datetime.date,
    rome_tz: pytz.BaseTzInfo,
) -> List[Dict[str, Any]]:
    """
    Estrae le 24 letture orarie (00:00 - 23:00) per la giornata indicata.
    Gestisce automaticamente l'ora solare (CET) e l'ora legale (CEST)
    attraverso il fuso orario 'Europe/Rome'.
    """
    valore_max_t = rileva_valore_massimo_temperatura(file_termo_path)

    # Scansione per tutte le 24 ore della giornata
    raw_termo: Dict[int, Optional[int]] = {}
    raw_igro: Dict[int, Optional[int]] = {}

    for h in sorted(MAPPA_ORE_OGGI.keys()):
        x_px = MAPPA_ORE_OGGI[h]
        raw_termo[h] = trova_pixel_blu_in_colonna(file_termo_path, x_px)
        raw_igro[h] = trova_pixel_blu_in_colonna(file_igro_path, x_px)

    records: List[Dict[str, Any]] = []

    for h in sorted(MAPPA_ORE_OGGI.keys()):
        # Costruzione del datetime locale con gestione dell'ora solare/legale
        naive_dt = datetime(
            data_riferimento.year,
            data_riferimento.month,
            data_riferimento.day,
            h,
            0,
            0
        )
        local_dt = rome_tz.localize(naive_dt, is_dst=None)
        
        # Identificazione se in quel momento vige CET (solare) o CEST (legale)
        fuso_codice = local_dt.tzname()  # 'CET' (+0100) oppure 'CEST' (+0200)
        iso_timestamp = local_dt.isoformat()

        y_t = raw_termo.get(h)
        y_rh = raw_igro.get(h)

        t_val: Optional[float] = None
        rh_val: Optional[float] = None
        stato = "OK"

        if y_t is not None:
            # Calcolo temperatura: Y_0 è 0°C, Y_MAX è valore_max_t
            t_calc = valore_max_t * ((Y_0 - y_t) / DY)
            t_val = round(max(0.0, min(t_calc, valore_max_t)), 1)
        else:
            stato = "DATO_TERMO_ASSENTE"

        if y_rh is not None:
            # Calcolo umidità relativa: Y_0 è 0%, Y_MAX è 100%
            rh_calc = VALORE_MAX_RH * ((Y_0 - y_rh) / DY)
            rh_val = round(max(0.0, min(rh_calc, VALORE_MAX_RH)), 1)
        else:
            if stato == "OK":
                stato = "DATO_IGRO_ASSENTE"
            else:
                stato = "DATO_ASSENTE"

        records.append({
            "timestamp": iso_timestamp,
            "data": data_riferimento.strftime("%Y-%m-%d"),
            "ora": f"{h:02d}:00",
            "fuso_orario": fuso_codice,
            "temperatura_c": t_val,
            "umidita_rh": rh_val,
            "stato_rilevamento": stato,
        })

    return records
