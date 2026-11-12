#!/usr/bin/env python3
"""Download 50+ real animal calls with reusable CC licences from Openverse."""
import json,re,subprocess,sys,time
from pathlib import Path
from urllib.parse import quote
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds";OUT.mkdir(parents=True,exist_ok=True)
API="https://api.openverse.org/v1/audio/"
S=requests.Session();S.headers.update({"User-Agent":"PastureAndroid/2.0 (offline animal soundboard; openverse API client)"})
ACCEPT={"by","by-sa","cc0","pdm"}
EXTS={"mp3","ogg","wav","oga","flac","m4a"}
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[
 {"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},
 {"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}
]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def norm(s):return re.sub(r"[^a-z0-9]+"," ",(s or "").lower()).strip()
def matches(a,result):
 hay=norm(result.get("title","")+" "+" ".join(t.get("name","") for t in result.get("tags",[])))
 aliases=[norm(x) for x in a.get("aliases",[])]
 for alias in aliases:
  if not alias:continue
  if re.search(r"(^| )"+re.escape(alias)+r"( |$)",hay):return True
 return False
def search(a):
 q=a["name"]+" animal sound"
 params={"q":q,"license":",".join(sorted(ACCEPT)),"license_type":"modification","category":"sound_effect","extension":",".join(sorted(EXTS)),"page_size":20,"mature":"false","filter_dead":"true"}
 for attempt in range(6):
  try:
   r=S.get(API,params=params,timeout=45)
   if r.status_code==429 or r.status_code>=500:
    delay=min(60,5*(2**attempt));print("Openverse rate limit; wait",delay,"seconds",flush=True);time.sleep(delay);continue
   r.raise_for_status();data=r.json()
   for item in data.get("results",[]):
    if item.get("license") not in ACCEPT:continue
    if item.get("category")!="sound_effect":continue
    if not matches(a,item):continue
    ext=(item.get("filetype") or "").lower()
    if ext not in EXTS:continue
    if item.get("url"):return item
   return None
  except Exception as e:
   delay=min(60,5*(2**attempt));print("Openverse search error",a["name"],e,"retry",attempt+1,flush=True);time.sleep(delay)
 return None
for n,a in enumerate(animals,1):
 print(f"[{n}/{len(animals)}] Searching {a['name']}",flush=True)
 found=search(a)
 if not found:
  print("  no matching openly licensed recording");time.sleep(3.2);continue
 url=found["url"];ext=(found.get("filetype") or "mp3").lower()
 tmp=OUT/(a["id"]+".source");target=OUT/(a["id"]+".mp3")
 try:
  with S.get(url,stream=True,timeout=90) as r:
   r.raise_for_status()
   with open(tmp,"wb") as f:
    for chunk in r.iter_content(262144):
     if chunk:f.write(chunk)
  subprocess.run(["ffmpeg","-y","-v","error","-i",str(tmp),"-t","8","-ac","1","-ar","22050","-b:a","80k",str(target)],check=True)
  tmp.unlink(missing_ok=True)
  source=found.get("foreign_landing_url") or found.get("detail_url") or url
  author=found.get("creator") or "Unknown"
  lic=found.get("license","").upper()+" "+str(found.get("license_version",""))
  manifest.append({**a,"audio":"sounds/"+target.name,"source":source,"author":author,"license":lic,"licenseUrl":found.get("license_url",""),"originalTitle":found.get("title",""),"provider":found.get("provider","")})
  credits.append(f"{a['name']}: {author}; {lic}; source {source}; license {found.get('license_url','')}; trimmed and converted to mono MP3.")
  print("  OK:",found.get("title"),"by",author,lic,flush=True)
 except Exception as e:
  print("  download/convert failed:",e);tmp.unlink(missing_ok=True);target.unlink(missing_ok=True)
 time.sleep(3.2)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2;print("New animal recordings:",added)
if added<50:sys.exit("Build stopped: fewer than 50 unique openly licensed animal recordings were found.")
