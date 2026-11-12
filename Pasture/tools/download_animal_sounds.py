#!/usr/bin/env python3
"""Fetch 50+ real animal calls with reusable CC licences from Openverse."""
import json,re,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds";OUT.mkdir(parents=True,exist_ok=True)
API="https://api.openverse.org/v1/audio/"
HEADERS={"User-Agent":"PastureAndroid/2.0 (offline animal soundboard)"}
ACCEPT={"by","by-sa","cc0","pdm"};EXTS={"mp3","ogg","wav","oga","flac","m4a"}
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[{"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},{"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def norm(s):return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
def matches(a,item):
 hay=norm(item.get("title","")+" "+" ".join(t.get("name","") for t in item.get("tags",[])))
 return any(re.search(r"(^| )"+re.escape(norm(x))+r"( |$)",hay) for x in a.get("aliases",[]) if norm(x))
def find_one(a):
 params={"q":a["name"]+" sound","license":",".join(sorted(ACCEPT)),"page_size":20,"page":1}
 try:
  r=requests.get(API,params=params,headers=HEADERS,timeout=(5,10))
  if r.status_code!=200:return a,None
  for item in r.json().get("results",[]):
   if item.get("license") in ACCEPT and (item.get("filetype") or "").lower() in EXTS and item.get("url") and item.get("category")!="music" and item.get("provider")!="jamendo" and matches(a,item):
    return a,item
 except Exception as e:print("Search failed",a["name"],e,flush=True)
 return a,None
selected={}
# Five requests per batch, then a 15-second pause: stays near Openverse's anonymous rate limit.
for start in range(0,len(animals),5):
 batch=animals[start:start+5]
 print("Searching:",", ".join(a["name"] for a in batch),flush=True)
 with ThreadPoolExecutor(max_workers=5) as pool:
  found=list(pool.map(find_one,batch))
 for a,item in found:
  if item:selected[a["id"]]=item
  else:print("  no open recording:",a["name"],flush=True)
 if start+5<len(animals):time.sleep(15)
print("Matched species:",len(selected),"/",len(animals),flush=True)
def download_one(pair):
 a,item=pair
 target=OUT/(a["id"]+".mp3");tmp=OUT/(a["id"]+".source")
 try:
  for attempt in range(4):
   with requests.get(item["url"],headers=HEADERS,stream=True,timeout=(8,20)) as r:
    if r.status_code==429:
     delay=min(20,int(r.headers.get("Retry-After") or (6*(attempt+1))))
     print("Audio host rate limited",a["name"],"retry in",delay,"s",flush=True)
     time.sleep(delay)
     continue
    r.raise_for_status()
    total=0
    with open(tmp,"wb") as f:
     for chunk in r.iter_content(131072):
      if not chunk:continue
      remain=4*1024*1024-total
      if remain<=0:break
      if len(chunk)>remain:chunk=chunk[:remain]
      f.write(chunk);total+=len(chunk)
      if total>=4*1024*1024:break
    break
  if not tmp.exists() or tmp.stat().st_size<1000:raise ValueError("no audio data downloaded")
  subprocess.run(["ffmpeg","-y","-v","error","-i",str(tmp),"-t","8","-ac","1","-ar","22050","-b:a","80k",str(target)],check=True,timeout=30)
  if not target.exists() or target.stat().st_size<1000:raise ValueError("empty converted audio")
  tmp.unlink(missing_ok=True)
  source=item.get("foreign_landing_url") or item.get("detail_url") or item["url"]
  author=item.get("creator") or "Unknown";lic=item.get("license","").upper()+" "+str(item.get("license_version",""))
  credit=f"{a['name']}: {author}; {lic}; source {source}; license {item.get('license_url','')}; trimmed and converted to mono MP3."
  entry={**a,"audio":"sounds/"+target.name,"source":source,"author":author,"license":lic,"licenseUrl":item.get("license_url",""),"originalTitle":item.get("title",""),"provider":item.get("provider","")}
  return entry,credit
 except Exception as e:
  print("Download failed",a["name"],e,flush=True);tmp.unlink(missing_ok=True);target.unlink(missing_ok=True);return None,None
pairs=[(a,selected[a["id"]]) for a in animals if a["id"] in selected]
with ThreadPoolExecutor(max_workers=2) as pool:
 downloaded=list(pool.map(download_one,pairs))
for entry,credit in downloaded:
 if entry:manifest.append(entry);credits.append(credit)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"animals-data.js").write_text("window.PASTURE_ANIMALS = "+json.dumps(manifest,ensure_ascii=False,separators=(",",":"))+";\\n",encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2;print("New animal recordings:",added)
if added<50:sys.exit("Build stopped: fewer than 50 unique openly licensed animal recordings were found.")
