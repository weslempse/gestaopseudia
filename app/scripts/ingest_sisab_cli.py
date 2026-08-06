import argparse
from app.etl.sisab import ingest_sisab_file

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="Caminho para o arquivo SISAB (ex: data/incoming/sisab/temas/02/2026/arquivo.xlsx)")
    args = p.parse_args()
    res = ingest_sisab_file(args.path)
    print(res)

if __name__ == "__main__":
    main()
