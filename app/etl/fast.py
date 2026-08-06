import pandas as pd
from sqlalchemy import text
from app.db import models
from app.utils.fileutils import sha256_of_file, parse_path_period
import hashlib
import os

# Placeholder mapper: adjust after you send FAST sample
# Expect columns: INEP, Data Evento, Data Digitacao, Tema/Pratica, Agent, PatientID

FAST_COLUMN_MAP = {
    # examples: "INEP": "inep", "Data Evento": "event_date"
}

def read_fast_excel(path):
    df = pd.read_excel(path, header=0, dtype=str)
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df

def normalize_fast_df(df):
    # This function must be customized based on actual FAST columns.
    # Attempt generic conversions if common names found
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if 'inep' in lc:
            col_map[c] = 'inep'
        elif 'data' in lc and ('evento' in lc or 'data evento' in lc or 'evento' in lc):
            col_map[c] = 'event_date'
        elif 'digita' in lc or 'digitação' in lc or 'data dig' in lc:
            col_map[c] = 'fast_digitization_date'
        elif 'tema' in lc or 'pratic' in lc:
            col_map[c] = 'item_raw'
        elif 'agent' in lc or 'agente' in lc:
            col_map[c] = 'agent_id'
        elif 'cpf' in lc or 'nis' in lc or 'patient' in lc:
            col_map[c] = 'patient_id'
    df = df.rename(columns=col_map)
    # parse dates dayfirst=True
    if 'event_date' in df.columns:
        df['event_date'] = pd.to_datetime(df['event_date'], dayfirst=True, errors='coerce').dt.date
    if 'fast_digitization_date' in df.columns:
        df['fast_digitization_date'] = pd.to_datetime(df['fast_digitization_date'], dayfirst=True, errors='coerce').dt.date
    # create item_code from item_raw (simple normalization)
    if 'item_raw' in df.columns:
        df['item_code'] = df['item_raw'].astype(str).str.strip().str.normalize('NFKD')
    # compute row_hash
    df['row_hash'] = (df.fillna('').astype(str).agg('||'.join, axis=1)).apply(lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest())
    return df


def ingest_fast_file(path, unit_per_file=None, mode='replace'):
    source, category, period = parse_path_period(path)
    file_sha = sha256_of_file(path)
    filename = path.split(os.sep)[-1]
    df = read_fast_excel(path)
    df = normalize_fast_df(df)

    with models.engine.begin() as conn:
        res = conn.execute(text("INSERT INTO source_file (source_system, category, filename, period, file_sha, status, uploaded_at) VALUES (:ss,:cat,:fn,:period,:sha,'processing', datetime('now'))"), {"ss": source, "cat": category, "fn": filename, "period": period, "sha": file_sha})
        try:
            sf_id = res.fetchone()[0]
        except Exception:
            sf_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]

        if mode == 'replace' and unit_per_file:
            conn.execute(text("DELETE FROM fast_actions WHERE period = :period AND inep = :inep"), {"period": period, "inep": unit_per_file})

        insert_sql = text("INSERT OR IGNORE INTO fast_actions (period, inep, item_code, event_date, fast_digitization_date, agent_id, patient_id, row_hash, source_file_id) VALUES (:period,:inep,:item_code,:event_date,:fast_digitization_date,:agent_id,:patient_id,:row_hash,:sfid)")
        for _, row in df.iterrows():
            conn.execute(insert_sql, {
                "period": period,
                "inep": row.get('inep'),
                "item_code": row.get('item_code'),
                "event_date": row.get('event_date'),
                "fast_digitization_date": row.get('fast_digitization_date'),
                "agent_id": row.get('agent_id'),
                "patient_id": row.get('patient_id'),
                "row_hash": row.get('row_hash'),
                "sfid": sf_id
            })

        conn.execute(text("UPDATE source_file SET processed_at = datetime('now'), status = 'done' WHERE id = :id"), {"id": sf_id})

    return {"status": "done", "source_file_id": sf_id, "period": period, "rows": len(df)}
