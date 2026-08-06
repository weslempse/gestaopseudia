-- init.sql (SQLite compatible)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_file (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_system TEXT NOT NULL,
  category TEXT,
  filename TEXT,
  period TEXT,
  file_sha TEXT,
  status TEXT,
  uploaded_at DATETIME DEFAULT (datetime('now')),
  processed_at DATETIME
);

CREATE TABLE IF NOT EXISTS sisab_counts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_system TEXT NOT NULL,
  category TEXT,
  period TEXT NOT NULL,
  uf TEXT,
  ibge TEXT,
  municipio TEXT,
  inep TEXT,
  item_code TEXT,
  count INTEGER,
  source_file_id INTEGER,
  FOREIGN KEY(source_file_id) REFERENCES source_file(id)
);

CREATE TABLE IF NOT EXISTS fast_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period TEXT,
  inep TEXT,
  item_code TEXT,
  event_date DATE,
  fast_digitization_date DATE,
  agent_id TEXT,
  patient_id TEXT,
  row_hash TEXT UNIQUE,
  source_file_id INTEGER,
  FOREIGN KEY(source_file_id) REFERENCES source_file(id)
);
