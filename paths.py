import os

def get_data_dir():
    # Usa %APPDATA% en Windows o ~ (home) en otros sistemas
    base = os.environ.get('APPDATA', os.path.expanduser('~'))
    data_dir = os.path.join(base, "Tech RioStore", "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()

def rel_to_data(filename):
    """Convierte nombre de archivo relativo en ruta absoluta dentro de la carpeta de datos."""
    return os.path.join(DATA_DIR, filename)

import os

def get_pdf_backup_dir():
    # Usa %APPDATA% en Windows, o home en otros sistemas
    base = os.environ.get('APPDATA', os.path.expanduser('~'))
    backup_dir = os.path.join(base, "pdf_backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir
