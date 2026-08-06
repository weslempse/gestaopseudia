import pandas as pd
from sqlalchemy import text
from app.db import models
from app.utils.fileutils import sha256_of_file, parse_path_period
import os

# column maps
THEME_COL_MAP = {
    "Agravos negligenciados": "agravos_negligenciados",
    "Alimentação saudável": "alimentacao_saudavel",
    "Autocuidado de pessoas com doe": "autocuidado",
    "Ações de combate ao\u00A0Aedes aegy": "combate_aedes",
    "Cidadania e direitos humanos": "cidadania_direitos",
    "Dependência química / tabaco /": "dependencia_quimica",
    "Envelhecimento / Climatério /": "envelhecimento",
    "Plantas medicinais / fitoterap": "plantas_medicinais",
    "Prevenção da violência e promo": "prevencao_violencia",
    "Saúde ambiental": "saude_ambiental",
    "Saúde bucal": "saude_bucal",
    "Saúde do trabalhador": "saude_trabalhador",
    "Saúde mental": "saude_mental",
    "Saúde sexual e reprodutiva": "saude_sexual_reprodutiva",
    "Semana saúde na escola": "semana_saude_escola",
}

PRACTICE_COL_MAP = {
    "Antropometria": "antropometria",
    "Aplicação tópica de flúor": "aplicacao_topica_fluor",
    "Desenvolvimento da linguagem": "desenvolvimento_linguagem",
    "Escovação dental supervisionad": "escovacao_dental_supervisionada",
    "Outro procedimento coletivo": "outro_procedimento_coletivo",
    "Programa nacional de controle ": "programa_nacional_controle",
    "Práticas corporais / atividade": "praticas_corporais",
    "Saúde auditiva": "saude_auditiva",
    "Saúde ocular": "saude_ocular",
    "Verificação da situação vacina": "verificacao_vacina",
}


def read_sisab_counts_excel(path):
    df = pd.read_excel(path, header=9, dtype=str)
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    return df


def melt_and_normalize(df, col_map):
    rename = {}
    for raw, code in col_map.items():
        if raw in df.columns:
            rename[raw] = code
    id_cols = {}
    for c in ["Uf", "Ibge", "Municipio", "INEP (Escolas/Creche)"]:
        if c in df.columns:
            id_cols[c] = c.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            rename[c] = id_cols[c]
    df = df.rename(columns=rename)
    id_cols_norm = list(id_cols.values())
    item_cols = [c for c in df.columns if c not in id_cols_norm]
    for c in item_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'\D', '', regex=True), errors='coerce').fillna(0).astype(int)
    df_long = df.melt(id_vars=id_cols_norm, value_vars=item_cols, var_name='item_code', value_name='count')
    return df_long


def ingest_sisab_file(path):
    source, category, period = parse_path_period(path)
    file_sha = sha256_of_file(path)
    filename = os.path.basename(path)
    df = read_sisab_counts_excel(path)
    col_map = THEME_COL_MAP if category == 'temas' else PRACTICE_COL_MAP
    df_long = melt_and_normalize(df, col_map)

    with models.engine.begin() as conn:
        res = conn.execute(text("""
            INSERT INTO source_file (source_system, category, filename, period, file_sha, status, uploaded_at)
            VALUES (:ss,:cat,:fn,:period,:sha,'processing', datetime('now'))
            RETURNING id
        """), {"ss": source, "cat": category, "fn": filename, "period": period, "sha": file_sha})
        # SQLite does not support RETURNING prior to newer versions; handle fallback
        try:
            sf_id = res.fetchone()[0]
        except Exception:
            sf_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]

        conn.execute(text("DELETE FROM sisab_counts WHERE source_system = :ss AND category = :cat AND period = :period"), {"ss": source, "cat": category, "period": period})

        insert_sql = text("""
            INSERT INTO sisab_counts (
                source_system, category, period, uf, ibge, municipio, inep, item_code, count, source_file_id
            ) VALUES (:ss,:cat,:period,:uf,:ibge,:municipio,:inep,:item_code,:count,:sfid)
        """)
        for _, row in df_long.iterrows():
            conn.execute(insert_sql, {
                "ss": source,
                "cat": category,
                "period": period,
                "uf": row.get('uf'),
                "ibge": row.get('ibge'),
                "municipio": row.get('municipio'),
                "inep": row.get('inep'),
                "item_code": row.get('item_code'),
                "count": int(row.get('count') or 0),
                "sfid": sf_id
            })

        conn.execute(text("UPDATE source_file SET processed_at = datetime('now'), status = 'done' WHERE id = :id"), {"id": sf_id})
    return {"status": "done", "source_file_id": sf_id, "period": period, "rows": len(df_long)}
