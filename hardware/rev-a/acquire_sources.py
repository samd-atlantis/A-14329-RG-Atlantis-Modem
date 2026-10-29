from pathlib import Path
import urllib.request, concurrent.futures, hashlib, json

ROOT=Path(__file__).resolve().parent
SOURCES={
 'hlk.pdf':'https://h.hlktech.com/download/HLK-7628N/1/HLK-7628N%E7%A1%AC%E4%BB%B6%E6%89%8B%E5%86%8CV2.6.pdf',
 'ai-wb2.pdf':'https://en.ai-thinker.com/Uploads/file/20220930/20220930121135_29921.pdf',
 'tps62132.pdf':'https://www.ti.com/lit/ds/symlink/tps62132.pdf',
 'sim-switch.pdf':'https://www.ti.com/lit/ds/symlink/ts3a44159.pdf',
 'acdc.pdf':'https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF',
 'quectel-product.html':'https://www.quectel.com/product/lte-eg25-gl-mini-pcie/',
 'kicad-download.html':'https://downloads.kicad.org/kicad/windows/explore/stable',
 'magjack.pdf':'https://www.we-online.com/components/products/datasheet/7499010121A.pdf',
 'euicc.pdf':'https://www.st.com/resource/en/data_brief/st4sim-200m.pdf',
 'usb-esd.pdf':'https://www.ti.com/lit/ds/symlink/tpd2eusb30.pdf',
 'wifi-switch.pdf':'https://www.ti.com/lit/ds/symlink/tps22918.pdf',
 'quectel-hardware.pdf':'https://manuals.plus/m/e0bca78a5dc0c0f3bbf234764f826f6b81548d5558890c74a850cad912649003.pdf',
 'gpio-expander.pdf':'https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23008-and-MCP23008-Data-Sheet-DS20001919.pdf',
 'usb-switch.pdf':'https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf',
 'uart-buffer.pdf':'https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf',
}
def get(item):
 name,url=item
 try:
  dest=ROOT/'references'/name;dest.parent.mkdir(exist_ok=True)
  data=dest.read_bytes() if dest.exists() else urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
  dest.write_bytes(data)
  return dict(file=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:return dict(file=name,url=url,error=str(e))
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex: result=list(ex.map(get,SOURCES.items()))
 (ROOT/'references'/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf8')
 print(json.dumps(result,indent=2))
