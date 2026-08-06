import hashlib, re, os

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def parse_path_period(path):
    # accepts: fast/02/2026/arquivo.xlsx or sisab/temas/02/2026/arquivo.xlsx
    m = re.search(r'([^/\\]+)(?:[/\\]([^/\\]+))?[/\\](\d{2})[/\\](\d{4})', path)
    if not m:
        raise ValueError("Caminho inválido; use algo como 'sisab/temas/02/2026/arquivo.xlsx')
    source = m.group(1).lower()
    category = m.group(2).lower() if m.group(2) else None
    month = m.group(3)
    year = m.group(4)
    period = f"{year}-{month}"
    return source, category, period
