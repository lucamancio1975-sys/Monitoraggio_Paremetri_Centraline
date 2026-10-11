# Monitoraggio Parametri Centraline CFR Toscana 🌦️

Archivio automatizzato per il monitoraggio giornaliero continuo dei parametri ambientali (**termometria** e **igrometria**) da stazioni meteo pubbliche del **CFR Toscana** (Centro Funzionale Regionale).

L'aggiornamento avviene ogni sera alle **23:50** (ora italiana) tramite **GitHub Actions**, che scarica i grafici generati dal CFR, ne estrae le curve orarie con algoritmi avanzati di Computer Vision (OpenCV) e archivia i dati progressivi in formati standard **CSV** e **JSON**.

---

## 📌 Stazioni Monitorate

Attualmente il sistema monitora **11 centraline**:

| Stazione | Codice CFR | File CSV Dedicato | File JSON Dedicato |
| :--- | :--- | :--- | :--- |
| **San Donato** | `TOS03003099` | `dati/stazioni/san_donato.csv` | `dati/stazioni/san_donato.json` |
| **Capalbio** | `TOS11000006` | `dati/stazioni/capalbio.csv` | `dati/stazioni/capalbio.json` |
| **Rispescia** | `TOS11000005` | `dati/stazioni/rispescia.csv` | `dati/stazioni/rispescia.json` |
| **Braccagni** | `TOS11000008` | `dati/stazioni/braccagni.csv` | `dati/stazioni/braccagni.json` |
| **Manciano** | `TOS03003079` | `dati/stazioni/manciano.csv` | `dati/stazioni/manciano.json` |
| **Pitigliano** | `TOS11000014` | `dati/stazioni/pitigliano.csv` | `dati/stazioni/pitigliano.json` |
| **Stiacciole** | `TOS11000042` | `dati/stazioni/stiacciole.csv` | `dati/stazioni/stiacciole.json` |
| **Valpiana** | `TOS11000041` | `dati/stazioni/valpiana.csv` | `dati/stazioni/valpiana.json` |
| **Follonica** | `TOS03002459` | `dati/stazioni/follonica.csv` | `dati/stazioni/follonica.json` |
| **Montenero** | `TOS11000051` | `dati/stazioni/montenero.csv` | `dati/stazioni/montenero.json` |
| **Castiglion Fiorentino** | `TOS11000038` | `dati/stazioni/castiglion_fiorentino.csv` | `dati/stazioni/castiglion_fiorentino.json` |

Oltre ai file divisi per centralina, è sempre aggiornato un database cumulativo completo:
* `dati/archivio_completo.csv`
* `dati/archivio_completo.json`

---

## 🕒 Gestione Automatica dell'Ora Solare e Legale (CET / CEST)

Poiché il CFR Toscana adotta l'orologio locale italiano nei suoi grafici, il sistema gestisce l'ora solare e legale a due livelli:
1. **GitHub Actions**: il trigger è pianificato su due orari UTC (`21:50 UTC` e `22:50 UTC`). Lo script Python integra un controllo orario locale (`--cron-guard`) che verifica l'ora esatta nel fuso orario `Europe/Rome`, attivando l'acquisizione solo alle 23:50 effettive in entrambi i periodi dell'anno.
2. **Tracciamento Dati**: ogni record memorizza il fuso orario di riferimento (`CET` per l'ora solare UTC+1, `CEST` per l'ora legale UTC+2) e il timestamp in formato completo ISO-8601 con offset (es. `+01:00` o `+02:00`), garantendo massima trasparenza e continuità per le serie temporali.

---

## 📊 Struttura dei Dati Archiviati

Campi disponibili nei file CSV:
* `timestamp`: data e ora ISO-8601 con offset di fuso orario (es. `2026-10-11T14:00:00+02:00`)
* `data`: data di riferimento (`YYYY-MM-DD`)
* `ora`: ora locale (`HH:00`)
* `fuso_orario`: regime orario in vigore (`CET` o `CEST`)
* `stazione`: nome della centralina
* `id_stazione`: codice identificativo univoco CFR
* `temperatura_c`: valore numerico di temperatura in °C (risoluzione $0.1\,^\circ\text{C}$)
* `umidita_rh`: valore numerico di umidità relativa in % (risoluzione $0.1\%$)
* `stato_rilevamento`: stato del dato (`OK`, `DATO_ASSENTE`)

---

## ⚙️ Esecuzione in Locale

### 1. Installazione requisiti
```bash
pip install -r requirements.txt
```

### 2. Aggiornamento manuale
Per aggiornare la giornata odierna:
```bash
python -m src.main
```

Per aggiornare una data specifica (utile per backfill o test):
```bash
python -m src.main --data 2026-10-11
```
