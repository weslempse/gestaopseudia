# gestaopseudia

Repositorio privado: protótipo para ingestão e reconciliação de arquivos SISAB (temas/práticas) e FAST.

Objetivos:
- Ingestão de arquivos SISAB (temas e práticas) com header na linha 10
- Armazenamento local (SQLite por padrão) para execução 100% local/grátis
- API FastAPI para upload de arquivos e endpoint de reconciliação
- Mapeadores configuráveis e placeholders para integrar FAST

Como usar (local, rápido):
1. Copie .env.sample para .env e edite conforme necessário (NÃO comitar .env)
   cp .env.sample .env

2. Construir e rodar com Docker Compose (opcional):
   docker-compose up --build

3. Ou rodar localmente sem Docker:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export DATABASE_URL="sqlite:///./data/healthdb.sqlite3"
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Upload via API:
  curl -F "file=@/caminho/para/arquivo.xlsx" -F "path=sisab/temas/02/2026" http://localhost:8000/upload/

Ingestão local via CLI:
  python -m app.scripts.ingest_sisab_cli ./data/incoming/sisab/temas/02/2026/arquivo.xlsx

Próximos passos:
- Forneça 5–10 linhas do arquivo FAST para eu finalizar o mapeador e a rotina de reconciliação por agregação (60 dias).
- Configure suas credenciais (MinIO, Postgres) localmente no .env se desejar usar serviços externos.
