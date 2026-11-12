#!/usr/bin/env python3
"""Bundle 50+ real, openly licensed animal calls from the MfN Berlin sound archive."""
import json,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds"; OUT.mkdir(parents=True,exist_ok=True)
API="https://commons.wikimedia.org/w/api.php"
CATEGORY="Category:Tierstimmen im Archiv des Museums für Naturkunde Berlin"
S=requests.Session()
S.headers.update({"User-Agent":"PastureAndroid/2.0 (offline educational animal soundboard; source: Wikimedia Commons)"})
EXTS=(".ogg",".oga",".opus",".wav",".mp3",".flac",".aiff",".m4a")
LICENSE=re.compile(r"(CC BY(?:-SA)? [234]\.0|CC0|Public domain)",re.I)
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[
 {"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},
 {"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}
]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def plain(x): return re.sub("<[^>]+>"," ",x or "").lower()
def archive_files():
 params={"action":"query","format":"json","generator":"categorymembers","gcmtitle":CATEGORY,"gcmtype":"file","gcmlimit":500,"prop":"imageinfo","iiprop":"url|extmetadata"}
 for attempt in range(7):
  try:
   r=S.get(API,params=params,timeout=90)
   if r.status_code==429 or r.status_code>=500:
    delay=min(60,5*(2**attempt)); print("Commons throttled; retrying in",delay,"seconds",flush=True);time.sleep(delay);continue
   r.raise_for_status()
   pages=list((r.json().get("query",{}).get("pages",{}) or {}).values())
   print("Commons archive returned",len(pages),"media files",flush=True)
   return pages
  except Exception as e:
   delay=min(60,5*(2**attempt));print("Commons archive request failed:",e,"retry",attempt+1,flush=True);time.sleep(delay)
 return []
pages=archive_files()
if not pages:
 sys.exit("Could not retrieve the licensed Museum für Naturkunde animal-sound collection.")
def match(a):
 aliases=[x.lower() for x in a.get("aliases",[])]
 for p in pages:
  ii=(p.get("imageinfo") or [{}])[0]; url=ii.get("url","")
  if not url.lower().endswith(EXTS): continue
  meta=ii.get("extmetadata") or {}
  lic=plain(meta.get("LicenseShortName",{}).get("value",""))
  if not LICENSE.search(lic): continue
  title=plain(p.get("title",""))
  desc=plain(meta.get("ImageDescription",{}).get("value",""))
  hay=title+" "+desc
  if any(alias and alias in hay for alias in aliases):
   return p,ii,meta,lic
 return None
print("Sample archive titles:", " | ".join(p.get("title","") for p in pages[:35]),flush=True)
for n,a in enumerate(animals,1):
 print(f"[{n}/{len(animals)}] {a['name']}",flush=True)
 found=match(a)
 if not found:
  print("  no direct species match");continue
 p,ii,meta,lic=found; title=p.get("title",""); src=ii.get("descriptionurl","")
 author=re.sub("<[^>]+>","",meta.get("Artist",{}).get("value","")).strip() or "Unknown"
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
  print("  download/convert failed:",e);tmp.unlink(missing_ok=True);target.unlink(missing_ok=True)
  time.sleep(1)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2
print("New redistributable animal recordings:",added)
if added<50:
 print("Available archive file titles for further matching:")
 for p in pages: print(" - "+p.get("title",""))
 sys.exit("Build stopped: fewer than 50 matching, licensed recordings were found.")
