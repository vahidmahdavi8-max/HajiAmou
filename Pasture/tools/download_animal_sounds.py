#!/usr/bin/env python3
"""Bundle 50+ real animal calls with reusable open licences from Openverse."""
import json,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds";OUT.mkdir(parents=True,exist_ok=True)
API="https://api.openverse.org/v1/audio/"
S=requests.Session();S.headers.update({"User-Agent":"PastureAndroid/2.0 (offline animal soundboard)"})
ACCEPT={"by","by-sa","cc0","pdm"};EXTS={"mp3","ogg","wav","oga","flac","m4a"}
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[{"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},{"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def norm(s):return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
def matches(a,item):
 hay=norm(item.get("title","")+" "+" ".join(t.get("name","") for t in item.get("tags",[])))
 return any(re.search(r"(^| )"+re.escape(norm(x))+r"( |$)",hay) for x in a.get("aliases",[]) if norm(x))
def api_search(q,page):
 params={"q":q,"license":",".join(sorted(ACCEPT)),"license_type":"modification","category":"sound_effect","extension":",".join(sorted(EXTS)),"page_size":20,"page":page,"mature":"false","filter_dead":"true"}
 for attempt in range(2):
  try:
   r=S.get(API,params=params,timeout=(8,15))
   if r.status_code==429 or r.status_code>=500:
    time.sleep(4*(attempt+1));continue
   if r.status_code>=400:
    print("Openverse rejected query",r.status_code,r.text[:150],flush=True);return []
   return r.json().get("results",[])
  except Exception as e:
   print("Openverse query error:",e,flush=True);time.sleep(3)
 return []
# Search in five batches, reducing API calls while keeping each species query explicit.
results=[]
for start in range(0,len(animals),10):
 group=animals[start:start+10]
 q="("+" | ".join(a["name"].lower() for a in group)+") sound"
 print("Searching batch:",", ".join(a["name"] for a in group),flush=True)
 for page in range(1,6):
  batch=api_search(q,page)
  if not batch:break
  results.extend(batch)
  time.sleep(3.1)
# Keep only unique, correctly tagged results under a redistribution-friendly licence.
selected={}
for a in animals:
 for item in results:
  if item.get("license") not in ACCEPT or item.get("category")!="sound_effect":continue
  if (item.get("filetype") or "").lower() not in EXTS or not item.get("url"):continue
  if matches(a,item):
   selected[a["id"]]=item;break
print("Matched species:",len(selected),"/",len(animals),flush=True)
for n,a in enumerate(animals,1):
 found=selected.get(a["id"])
 if not found:continue
 print(f"[{n}/{len(animals)}] Downloading {a['name']}",flush=True)
 target=OUT/(a["id"]+".mp3");tmp=OUT/(a["id"]+".source")
 try:
  with S.get(found["url"],stream=True,timeout=(10,20)) as r:
   r.raise_for_status()
   length=int(r.headers.get("Content-Length") or 0)
   if length>12*1024*1024:raise ValueError("source too large")
   total=0
   with open(tmp,"wb") as f:
    for chunk in r.iter_content(131072):
     if not chunk:continue
     total+=len(chunk)
     if total>12*1024*1024:raise ValueError("source exceeded 12 MB")
     f.write(chunk)
  subprocess.run(["ffmpeg","-y","-v","error","-i",str(tmp),"-t","8","-ac","1","-ar","22050","-b:a","80k",str(target)],check=True,timeout=35)
  if not target.exists() or target.stat().st_size<1000:raise ValueError("empty converted audio")
  tmp.unlink(missing_ok=True)
  source=found.get("foreign_landing_url") or found.get("detail_url") or found["url"]
  author=found.get("creator") or "Unknown";lic=found.get("license","").upper()+" "+str(found.get("license_version",""))
  manifest.append({**a,"audio":"sounds/"+target.name,"source":source,"author":author,"license":lic,"licenseUrl":found.get("license_url",""),"originalTitle":found.get("title",""),"provider":found.get("provider","")})
  credits.append(f"{a['name']}: {author}; {lic}; source {source}; license {found.get('license_url','')}; trimmed and converted to mono MP3.")
  print("  OK",found.get("title"),lic,flush=True)
 except Exception as e:
  print("  download failed:",e,flush=True);tmp.unlink(missing_ok=True);target.unlink(missing_ok=True)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2;print("New animal recordings:",added)
if added<50:sys.exit("Build stopped: fewer than 50 unique openly licensed animal recordings were found.")
