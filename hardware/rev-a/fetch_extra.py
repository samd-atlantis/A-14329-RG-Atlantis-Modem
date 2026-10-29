from pathlib import Path
import urllib.request,concurrent.futures,json,hashlib
R=Path(__file__).resolve().parent/'references'
items=[
 ('magjack.pdf','https://katalog.we-online.de/pbs/datasheet/7499010121A.pdf'),
 ('magjack-new.pdf','https://www.we-online.com/components/products/datasheet/7499010121A.pdf?download=1'),
 ('euicc.pdf','https://www.st.com.cn/resource/en/data_brief/st4sim-200m.pdf'),
 ('quectel-hardware.pdf','https://device.report/m/311c951a2cf5843f28bb2bfcc81a5a51f3287ed1bcb47fe0ad69a75262283fe3.pdf'),
 ('quectel-evb.pdf','https://www.quectel.com/content/uploads/2024/03/quectel_mini_pcie_evb_user_guide_v1-1.pdf'),
]
def get(item):
 name,url=item
 try:
  data=urllib.request.urlopen(url,timeout=20).read()
  if not data.startswith(b'%PDF'):raise ValueError('Not PDF')
  (R/name).write_bytes(data)
  return dict(file=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:return dict(file=name,url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:result=list(ex.map(get,items))
(R/'extra-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
