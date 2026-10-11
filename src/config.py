import os
from pathlib import Path

# --- PERCORSI CARTELLE E FILE ---
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
STAZIONI_FILE = CONFIG_DIR / "stazioni.json"
DATA_DIR = ROOT_DIR / "dati"
DATA_STAZIONI_DIR = DATA_DIR / "stazioni"
TEMP_DIR = ROOT_DIR / "scarichi_temp"

# Assicura esistenza cartelle essenziali
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_STAZIONI_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# --- COSTANTI DI CALIBRAZIONE GRAFICA (CFR TOSCANA) ---
# Origine e scala asse verticale (Y)
Y_0 = 376       # Pixel base corrispondente allo 0 (°C o %)
Y_MAX = 51      # Pixel massimo superiore del grafico
DY = Y_0 - Y_MAX  # Escursione totale: 325 pixel

# Fondo scala Umidità Relativa
VALORE_MAX_RH = 100.0

# Mappatura ore della giornata attuale (oggi) -> coordinate X dei pixel
# Le ore 00:00 - 23:00 corrispondono a questi indici orizzontali calibrati
MAPPA_ORE_OGGI = {
    0: 325,
    1: 336,
    2: 346,
    3: 357,
    4: 368,
    5: 378,
    6: 389,
    7: 400,
    8: 410,
    9: 421,
    10: 431,
    11: 442,
    12: 453,
    13: 464,
    14: 474,
    15: 485,
    16: 495,
    17: 506,
    18: 516,
    19: 527,
    20: 538,
    21: 549,
    22: 559,
    23: 570
}

# Parametri colore per Computer Vision (OpenCV)
COLORE_GRIGIO_GRIGLIA_BGR = (192, 192, 192)
TOLLERANZA_GRIGIO_LINEA = 12
TOLLERANZA_GRIGIO_COLONNA = 15

# Intervallo HSV per isolamento traccia blu (curva dati)
HSV_LOWER_BLUE = [95, 35, 40]
HSV_UPPER_BLUE = [135, 255, 255]

# --- PARAMETRI DI RETE ---
CFR_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0",
    "Referer": "https://www.cfr.toscana.it/monitoraggio/index.php",
}
DOWNLOAD_TIMEOUT = 30

# --- FUSO ORARIO E GESTIONE ORA SOLARE/LEGALE ---
TIMEZONE_ITALIA = "Europe/Rome"
