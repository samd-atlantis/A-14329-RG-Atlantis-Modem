from pathlib import Path
import urllib.request,urllib.parse,json,sys
sys.stdout.reconfigure(encoding='utf8')
R=Path(__file__).resolve().parent/'references'
u='https://h.hlktech.com/Mobile/Download/queryResouceInfo'
data=urllib.parse.urlencode({'id':'34'}).encode()
r=json.loads(urllib.request.urlopen(urllib.request.Request(u,data=data),timeout=20).read())
(R/'hlk-resource-index.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
for item in r.get('data',[]):
 print(item['resource_name'],item['resource_url'])
 if item.get('filesuffix') in ['.rar','.zip'] and ('7628N' in item['resource_name']) and ('底板' in item['resource_name']):
  url=item['resource_url'];url=('https://r0.hlktech.com'+url) if url.startswith('/') else url
  url=urllib.parse.quote(url,safe=':/?=&%')
  p=R/('hlk-carrier'+item['filesuffix'])
  urllib.request.urlretrieve(url,p);print('Saved',p,p.stat().st_size)
