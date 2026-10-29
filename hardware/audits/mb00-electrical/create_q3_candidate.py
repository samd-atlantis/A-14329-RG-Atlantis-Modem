"""Create a separate, narrow schematic-only correction; never edit the release."""
import json, zipfile, hashlib, copy
from collections import defaultdict
from audit import RELEASE,OUT,extract,schematic,pcb
source=RELEASE/"schematic-assembly49.epro2"
target=OUT/"schematic-mb00-Q3-proposed.epro2"
# Drain exits upward; source exits downward. Pin positions and nets do not change.
# Discover the actual label attribute IDs rather than assuming their sequence.
docs=extract(source);rows=next(d["records"] for d in docs if d["head"]["docType"]=="SCH_PAGE")
changes={"ed2700000000011e":{"endY":-1070},"ed27000000000126":{"endY":-830}}
for r in rows:
 b=r["b"]
 if r["h"]["type"]=="ATTR" and b.get("key")=="NET":
  if b.get("parentId")=="ed2700000000011d":changes[r["h"]["id"]]={"y":-1070}
  if b.get("parentId")=="ed27000000000125":changes[r["h"]["id"]]={"y":-830}
assert len(changes)==4
before={r["h"]["id"]:r for r in rows if r["h"]["id"] in changes}
assert before["ed2700000000011e"]["b"]["endY"]==-870
assert before["ed27000000000126"]["b"]["endY"]==-1030
plan=[]
for rid,fields in changes.items():
 old=before[rid];new=copy.deepcopy(old);new["b"].update(fields)
 plan.append(dict(record_id=rid,before=old,after=new))
count=defaultdict(int)
with zipfile.ZipFile(source) as zin,zipfile.ZipFile(target,"w") as zout:
 for info in zin.infolist():
  data=zin.read(info.filename)
  if info.filename.endswith(".epru"):
   rebuilt=[]
   for line in data.decode("utf-8-sig").splitlines(keepends=True):
    content=line.rstrip("\r\n");newline=line[len(content):]
    if "||" in content:
     hs,bs=content.removesuffix("|").split("||",1);h=json.loads(hs)
     if h.get("id") in changes and bs:
      b=json.loads(bs);b.update(changes[h["id"]]);content=hs+"||"+json.dumps(b,ensure_ascii=False,separators=(",",":"))+("|" if content.endswith("|") else "")
      count[h["id"]]+=1
    rebuilt.append(content+newline)
   data="".join(rebuilt).encode("utf-8")
  zout.writestr(info,data)
assert set(count)==set(changes)
sch=schematic(extract(target));pads,_=pcb(extract(RELEASE/"pcb-assembly49.epro2"));pm=defaultdict(set)
for p in pads:pm[p["ref"],p["pin"]].add(p["net"])
errors=[s for s in sch if s["conflicts"] or pm.get((s["ref"],s["pin"]))!={s["net"]}]
assert not errors,errors
# Proof that only four final records changed in the decoded schematic/documents.
a={(d["head"]["docType"],d["head"].get("uuid"),r["h"]["id"]):r for d in docs for r in d["records"]}
b={(d["head"]["docType"],d["head"].get("uuid"),r["h"]["id"]):r for d in extract(target) for r in d["records"]}
assert set(a)==set(b)
changed=[k for k in a if a[k]!=b[k]]
assert len(changed)==4
result=dict(status="PROPOSED_SCHEMATIC_ONLY_CORRECTION_NOT_LIVE_EASYEDA",original_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),candidate_file=target.name,changed_final_records=changed,changes=plan,matched_schematic_pin_keys=len(sch),remaining_mismatches=errors,frozen_release_unchanged=True,native_erc_rerun=False,limitations="Candidate needs import/review and native ERC; no PCB copper or manufacturing files were changed.")
OUT.joinpath("q3-correction-plan.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ["changes"]},indent=2))
