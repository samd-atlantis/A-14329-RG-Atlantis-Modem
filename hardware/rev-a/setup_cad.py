"""Download/extract local validation tools. Does not install KiCad system-wide."""
from pathlib import Path
import urllib.request, subprocess, concurrent.futures
R=Path(__file__).resolve().parents[2]/'.tools'
R.mkdir(exist_ok=True)
def fetch(url,name):
 p=R/name
 if not p.exists():
  print('Downloading',name,flush=True)
  urllib.request.urlretrieve(url,p)
 print(name,p.stat().st_size,flush=True)
 return p
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  fs=[ex.submit(fetch,'https://www.7-zip.org/a/7zr.exe','7zr.exe'),
      ex.submit(fetch,'https://github.com/KiCad/kicad-source-mirror/releases/download/9.0.7/kicad-9.0.7-x86_64.exe','kicad-9.0.7-x86_64.exe')]
  seven,installer=[f.result() for f in fs]
 # 7zr supports only 7z; use it to unpack the full standalone 7-Zip executable first.
 extra=fetch('https://www.7-zip.org/a/7z2301-extra.7z','7z-extra.7z')
 subprocess.run([str(seven),'x',str(extra),'-o'+str(R/'7zip'),'-y'],check=True,stdout=subprocess.DEVNULL)
 full=fetch('https://www.7-zip.org/a/7z2301-x64.exe','7z-full-installer.exe')
 subprocess.run([str(R/'7zip'/'7za.exe'),'x',str(full),'-o'+str(R/'7zip-full'),'-y'],check=True,stdout=subprocess.DEVNULL)
 print('Extracting KiCad local validation runtime',flush=True)
 subprocess.run([str(R/'7zip-full'/'7z.exe'),'x',str(installer),'-o'+str(R/'kicad'),'-y'],check=True,stdout=subprocess.DEVNULL)
 print('KiCad extracted',flush=True)
