import os
import sys
import platform
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path

# Araç indirme linkleri (Örnek versiyonlar veya 'latest' linkleri)
# Not: Bazı GitHub linkleri direkt 'latest/download' destekler.
TOOLS = {
    "ruff": {
        "win32/x64": "https://github.com/astral-sh/ruff/releases/latest/download/ruff-x86_64-pc-windows-msvc.zip",
        "linux/x64": "https://github.com/astral-sh/ruff/releases/latest/download/ruff-x86_64-unknown-linux-gnu.tar.gz",
        "format": "archive"
    },
    "biome": {
        "win32/x64": "https://github.com/biomejs/biome/releases/latest/download/biome-win32-x64.exe",
        "linux/x64": "https://github.com/biomejs/biome/releases/latest/download/biome-linux-x64",
        "format": "binary"
    },
    "oxlint": {
        "win32/x64": "https://github.com/oxc-project/oxc/releases/latest/download/oxlint-x86_64-pc-windows-msvc.exe",
        "linux/x64": "https://github.com/oxc-project/oxc/releases/latest/download/oxlint-x86_64-unknown-linux-gnu.tar.gz",
        "format": "mixed"
    },
    "gitleaks": {
        "win32/x64": "https://github.com/gitleaks/gitleaks/releases/download/v8.18.2/gitleaks_8.18.2_windows_x64.zip",
        "linux/x64": "https://github.com/gitleaks/gitleaks/releases/download/v8.18.2/gitleaks_8.18.2_linux_x64.tar.gz",
        "format": "archive"
    },
    "ripgrep": {
        "win32/x64": "https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-pc-windows-msvc.zip",
        "linux/x64": "https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz",
        "format": "archive"
    }
}

def get_platform_info():
    os_name = sys.platform
    machine = platform.machine().lower()
    if "64" in machine:
        arch = "x64"
    else:
        arch = "x86"
    return f"{os_name}/{arch}"

def setup_binaries():
    plat = get_platform_info()
    print(f"--- Master MCP Binary Kurulum Aracı ---")
    print(f"Tespit edilen platform: {plat}\n")
    
    project_root = Path(__file__).parent.parent
    bin_dir = project_root / "bin" / plat
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    for tool, info in TOOLS.items():
        if plat not in info:
            print(f"[!] {tool} için {plat} platformunda otomatik indirme desteklenmiyor.")
            continue
            
        url = info[plat]
        print(f"[*] {tool} indiriliyor: {url}")
        
        try:
            temp_file = bin_dir / f"temp_{tool}"
            urllib.request.urlretrieve(url, temp_file)
            
            # Arşiv ise aç, binary ise isimlendir
            if url.endswith(".zip"):
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(bin_dir)
                print(f"[+] {tool} başarıyla arşiften çıkarıldı.")
            elif url.endswith(".tar.gz"):
                with tarfile.open(temp_file, "r:gz") as tar_ref:
                    tar_ref.extractall(bin_dir)
                print(f"[+] {tool} başarıyla tar'dan çıkarıldı.")
            else:
                # Direkt binary
                ext = ".exe" if "win32" in plat else ""
                dest = bin_dir / f"{tool}{ext}"
                shutil.move(temp_file, dest)
                if os.name != "nt":
                    os.chmod(dest, 0o755)
                print(f"[+] {tool} binary olarak kaydedildi.")
                
            if temp_file.exists():
                os.remove(temp_file)
                
        except Exception as e:
            print(f"[ERR] {tool} kurulumu başarısız: {e}")

if __name__ == "__main__":
    if "--install" in sys.argv:
        setup_binaries()
    else:
        print("Kullanım: python setup_bins.py --install")
        print(f"Platformunuz ({get_platform_info()}) için kurulumu başlatır.")
