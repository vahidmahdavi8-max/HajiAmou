#!/usr/bin/env python3
"""Bundle real animal recordings from the CC BY-SA Tierstimmen collection."""
import json,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]/"app/src/main/assets"
OUT=ROOT/"sounds";OUT.mkdir(parents=True,exist_ok=True)
API="https://commons.wikimedia.org/w/api.php"
START="Category:Tierstimmen im Archiv des Museums für Naturkunde Berlin"
S=requests.Session();S.headers.update({"User-Agent":"PastureAndroid/2.0 (offline animal soundboard)"})
EXTS=(".ogg",".oga",".opus",".wav",".mp3",".flac",".aiff",".m4a")
LIC=re.compile(r"(CC BY(?:-SA)? [234]\.0|CC0|Public domain)",re.I)
animals=json.loads((ROOT/"animals.json").read_text(encoding="utf-8"))
manifest=[{"id":"cow","name":"Cow","emoji":"🐄","category":"Farm","call":"Moo","audio":"meadow/cow.mp3","source":"Original Pasture project","license":"Original project credit"},{"id":"sheep","name":"Sheep","emoji":"🐑","category":"Farm","call":"Baa","audio":"meadow/sheep-a.mp3","source":"earthcalling","license":"Public domain"}]
credits=["Cow: original Pasture recording; see original project credit.","Sheep: earthcalling; public-domain field recording."]
def plain(x):return re.sub("<[^>]+>"," ",x or "").lower()
def api(params):
 for attempt in range(6):
  try:
   r=S.get(API,params={"action":"query","format":"json",**params},timeout=60)
   if r.status_code==429 or r.status_code>=500:
    delay=min(45,5*(2**attempt));print("Commons throttle; wait",delay,flush=True);time.sleep(delay);continue
   r.raise_for_status();data=r.json()
   if data.get("warnings"):print("API warnings:",data["warnings"],flush=True)
   return data
  except Exception as e:
   delay=min(45,5*(2**attempt));print("API retry",attempt+1,e,flush=True);time.sleep(delay)
 return {}
def collect_files(category,depth=0,seen=None):
 if seen is None:seen=set()
 if category in seen or depth>3:return []
 seen.add(category)
 data=api({"list":"categorymembers","cmtitle":category,"cmtype":"all","cmlimit":500})
 members=data.get("query",{}).get("categorymembers",[])
 print("Category",category,"members",len(members),flush=True)
 files=[m["pageid"] for m in members if m.get("ns")==6]
 subcats=[m["title"] for m in members if m.get("ns")==14]
 for sub in subcats:files.extend(collect_files(sub,depth+1,seen))
 return files
ids=collect_files(START)
if not ids:
 # Find the live Commons category name, since the project page's suggested title may differ.
 d=api({"list":"search","srsearch":"Tierstimmen","srnamespace":14,"srlimit":30})
 cats=[x["title"] for x in d.get("query",{}).get("search",[])]
 print("Commons category search:",cats,flush=True)
 for c in cats:ids.extend(collect_files(c,0,set()))
ids=list(dict.fromkeys(ids))
print("Unique archive files:",len(ids),flush=True)
pages=[]
for start in range(0,len(ids),50):
 d=api({"pageids":"|".join(map(str,ids[start:start+50])),"prop":"imageinfo","iiprop":"url|extmetadata"})
 pages.extend((d.get("query",{}).get("pages",{}) or {}).values())
print("File metadata loaded:",len(pages),flush=True)
def match(a):
 aliases=[x.lower() for x in a.get("aliases",[])]
 for p in pages:
  ii=(p.get("imageinfo") or [{}])[0];url=ii.get("url","")
  if not url.lower().endswith(EXTS):continue
  meta=ii.get("extmetadata") or {};lic=plain(meta.get("LicenseShortName",{}).get("value",""))
  if not LIC.search(lic):continue
  hay=plain(p.get("title","")+" "+meta.get("ImageDescription",{}).get("value",""))
  if any(x and x in hay for x in aliases):return p,ii,meta,lic
 return None
for n,a in enumerate(animals,1):
 print(f"[{n}/{len(animals)}] {a['name']}",flush=True);found=match(a)
 if not found:continue
 p,ii,meta,lic=found;title=p.get("title","");src=ii.get("descriptionurl","")
 author=re.sub("<[^>]+>","",meta.get("Artist",{}).get("value","")).strip() or "Unknown"
 licurl=re.sub("<[^>]+>","",meta.get("LicenseUrl",{}).get("value","")).strip()
 tmp=OUT/(a["id"]+".source");target=OUT/(a["id"]+".mp3")
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
  print("  OK",title,lic,flush=True)
 except Exception as e:
  print("  download failed",e);tmp.unlink(missing_ok=True);target.unlink(missing_ok=True)
  time.sleep(1)
(ROOT/"animals.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(ROOT/"SOUND_CREDITS.txt").write_text("\n".join(credits)+"\n",encoding="utf-8")
added=len(manifest)-2;print("New animal recordings:",added)
if added<50:
 print("Available source files:",[p.get("title") for p in pages])
 sys.exit("Need at least 50 newly recorded species.")
