# tools/debug_smoke.py
import os, sys

ok = True
db = os.getenv("SUPABASE_DATABASE_URL")
if not db:
    print("DB: SUPABASE_DATABASE_URL missing")
    ok = False
else:
    print("DB: SUPABASE_DATABASE_URL present (not printed)")

sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/gdrive-sa.json")
if os.path.isfile(sa_file):
    print("SA: service account json file exists at", sa_file)
else:
    print("SA: service account json file NOT FOUND at", sa_file)
    ok = False

try:
    import psycopg2
    if db:
        try:
            conn = psycopg2.connect(db)
            conn.close()
            print("DB: connection test OK")
        except Exception as e:
            print("DB: connection test FAILED:", e)
            ok = False
except Exception as e:
    print("DB: psycopg2 not installed or import failed:", e)
    ok = False

if not ok:
    sys.exit(1)
print("SMOKE: OK")
