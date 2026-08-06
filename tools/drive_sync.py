import os
import io
import pathlib
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.utils.fileutils import sha256_of_file
from app.db import models
from sqlalchemy import text
from app.etl.sisab import ingest_sisab_file
from app.etl.fast import ingest_fast_file

# Config via env
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/gdrive-sa.json")
ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")  # required
INCOMING_DIR = os.getenv("INCOMING_DIR", "./data/incoming")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def list_folder_children(service, folder_id):
    items = []
    page_token = None
    q = f"'{folder_id}' in parents and trashed = false"
    while True:
        res = service.files().list(q=q,
                                   spaces='drive',
                                   fields="nextPageToken, files(id, name, mimeType, md5Checksum)",
                                   pageToken=page_token).execute()
        items.extend(res.get('files', []))
        page_token = res.get('nextPageToken', None)
        if page_token is None:
            break
    return items

def ensure_dir(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, mode='wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()

def file_already_processed(conn, file_sha):
    if not file_sha:
        return False
    r = conn.execute(text("SELECT id FROM source_file WHERE file_sha = :sha"), {"sha": file_sha}).fetchone()
    return r is not None

def traverse_and_download(service, folder_id, current_path=""):
    items = list_folder_children(service, folder_id)
    # Process folders first
    for it in items:
        if it['mimeType'] == 'application/vnd.google-apps.folder':
            subpath = os.path.join(current_path, it['name'])
            traverse_and_download(service, it['id'], subpath)
    # Then files
    for it in items:
        if it['mimeType'] != 'application/vnd.google-apps.folder':
            rel_dir = os.path.join(INCOMING_DIR, current_path)
            ensure_dir(rel_dir)
            dest = os.path.join(rel_dir, it['name'])
            try:
                with models.engine.begin() as conn:
                    md5 = it.get('md5Checksum')
                    if file_already_processed(conn, md5):
                        print(f"Skipping (already processed MD5): {it['name']} in {current_path}")
                        continue
                    print(f"Downloading {it['name']} to {dest}")
                    download_file(service, it['id'], dest)
                    sha = md5 or sha256_of_file(dest)
                    conn.execute(text("""
                        INSERT INTO source_file (source_system, category, filename, period, file_sha, status, uploaded_at)
                        VALUES (:ss,:cat,:fn,:period,:sha,'downloaded', datetime('now'))
                    """), {
                        "ss": current_path.split('/')[0] if current_path else 'drive',
                        "cat": current_path.split('/')[1] if len(current_path.split('/'))>1 else None,
                        "fn": it['name'],
                        "period": None,
                        "sha": sha
                    })
                # Decide ingestion based on path
                absolute_saved_path = os.path.join(INCOMING_DIR, current_path, it['name'])
                if current_path.startswith("sisab"):
                    print("Calling SISAB ingest for", absolute_saved_path)
                    res = ingest_sisab_file(absolute_saved_path)
                    print("SISAB ingest result:", res)
                elif current_path.startswith("fast"):
                    print("Calling FAST ingest for", absolute_saved_path)
                    res = ingest_fast_file(absolute_saved_path)
                    print("FAST ingest result:", res)
                else:
                    print("Downloaded file to unmapped folder:", dest)
            except Exception as e:
                print("Error processing file:", dest)
                traceback.print_exc()

def main():
    if not ROOT_FOLDER_ID:
        raise RuntimeError("Defina GOOGLE_DRIVE_ROOT_FOLDER_ID no ambiente com o ID da pasta root do Drive")
    svc = build_drive_service()
    traverse_and_download(svc, ROOT_FOLDER_ID, current_path="")

if __name__ == "__main__":
    main()
