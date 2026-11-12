#!/usr/bin/env python3
import json,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds"; OUT.mkdir(parents=True,exist_ok=True)
API="https://commons.wikimedia.org/w/api.php"
S=requests.Session(); S.headers.update({"User-Agent":"PastureAndroid/2.0 (offline animal soundboard)"})
OK=re.compile(r"(CC0|Public domain|CC BY(?:-SA)? [234]\.0)",re.I)
EXTS=(".ogg",".oga",".opus",".wav",".mp3",".flac",".aiff",".m4a")
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[
{"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},
{"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}
]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def plain(x): return re.sub("<[^>]+>"," ",x or "").lower()
def candidates(alias):
 p={"action":"query","format":"json","generator":"search","gsrsearch":'"'+alias+'" sound',"gsrnamespace":6,"gsrlimit":30,"prop":"imageinfo","iiprop":"url|extmetadata"}
 try:
  r=S.get(API,params=p,timeout=40); r.raise_for_status()
  return list((r.json().get("query",{}).get("pages",{}) or {}).values())
 except Exception as e:
  print("Search error",alias,e); return []
def choose(a):
 seen=set()
 for alias in a["aliases"]:
  for page in candidates(alias):
   title=page.get("title","")
   if title in seen: continue
   seen.add(title)
   ii=(page.get("imageinfo") or [{}])[0]; url=ii.get("url","")
   if not url.lower().endswith(EXTS): continue
   meta=ii.get("extmetadata") or {}
   license_name=plain(meta.get("LicenseShortName",{}).get("value",""))
   if not OK.search(license_name): continue
   hay=plain(title+" "+meta.get("ImageDescription",{}).get("value",""))
   if not any(x.lower() in hay for x in a["aliases"]): continue
   if any(x in hay for x in ["soundscape","ambience","compilation","collection"]): continue
   return page,ii,meta,license_name
 return None
for n,a in enumerate(animals,1):
 print(f"[{n}/{len(animals)}] {a['name']}",flush=True)
 found=choose(a)
 if not found:
  print("  no suitably licensed match"); continue
 page,ii,meta,lic=found; title=page.get("title","")
 src=ii.get("descriptionurl",""); author=re.sub("<[^>]+>","",meta.get("Artist",{}).get("value","")).strip() or "Unknown"
 licurl=re.sub("<[^>]+>","",meta.get("LicenseUrl",{}).get("value","")).strip()
 tmp=OUT/(a["id"]+".source"); target=OUT/(a["id"]+".mp3")
 try:
  with S.get(ii["url"],stream=True,timeout=90) as r:
   r.raise_for_status()
   with open(tmp,"wb") as f:
    for chunk in r.iter_content(262144):
     if chunk:f.write(chunk)
  subprocess.run(["ffmpeg","-y","-v","error","-i",str(tmp),"-t","8","-ac","1","-ar","22050","-b:a","80k",str(target)],check=True)
  tmp.unlink(missing_ok=True)
  manifest.append({**a,"audio":"sounds/"+target.name,"source":src,"author":author,"license":lic,"licenseUrl":licurl,"originalTitle":title})
  credits.append(f"{a['name']}: {author}; {lic}; source {src}; license {licurl}; trimmed and converted to mono MP3.")
  print("  OK:",title,lic,flush=True)
 except Exception as e:
  print("  download/convert failed:",e); tmp.unlink(missing_ok=True); target.unlink(missing_ok=True)
 time.sleep(.15)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2
print("New redistributable animal recordings:",added)
if added<50: sys.exit("Build stopped: fewer than 50 new licensed recordings were found.")
