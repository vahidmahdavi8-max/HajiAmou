#!/usr/bin/env python3
"""Bundle 50+ real animal calls with CC BY, CC BY-SA or CC0 licences from Openverse."""
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
def find_sound(a):
 queries=[a["name"]+" sound",a["name"]+" animal"]
 for q in queries:
  params={"q":q,"license":",".join(sorted(ACCEPT)),"page_size":20,"mature":"false","filter_dead":"true"}
  for page in (1,2):
   params["page"]=page
   try:
    r=S.get(API,params=params,timeout=(8,18))
    if r.status_code==429:
     print("Openverse rate limit; pausing 15s",flush=True);time.sleep(15);continue
    if r.status_code>=500:
     print("Openverse server response",r.status_code,flush=True);time.sleep(5);continue
    if r.status_code>=400:
     print("Openverse query rejected",r.status_code,r.text[:100],flush=True);break
    for item in r.json().get("results",[]):
     if item.get("license") in ACCEPT and (item.get("filetype") or "").lower() in EXTS and item.get("url") and item.get("category")!="music" and item.get("provider")!="jamendo" and matches(a,item):
      return item
   except Exception as e:print("Search error",q,e,flush=True)
   time.sleep(3.1)
 return None
for n,a in enumerate(animals,1):
 print(f"[{n}/{len(animals)}] Searching {a['name']}",flush=True)
 found=find_sound(a)
 if not found:
  print("  no suitable recording found",flush=True);continue
 target=OUT/(a["id"]+".mp3");tmp=OUT/(a["id"]+".source")
 try:
  with S.get(found["url"],stream=True,timeout=(10,20)) as r:
   r.raise_for_status();length=int(r.headers.get("Content-Length") or 0)
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
