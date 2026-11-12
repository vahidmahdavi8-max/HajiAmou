#!/usr/bin/env python3
import requests,json
u="https://api.openverse.org/v1/audio/"
s=requests.Session();s.headers.update({"User-Agent":"PastureAndroid/2.0"})
tests=[
 {"q":"horse","page_size":10},
 {"q":"horse sound","page_size":10,"category":"sound_effect"},
 {"q":"horse sound","page_size":10,"license":"by,by-sa,cc0,pdm"},
 {"q":"horse sound","page_size":10,"license":"by,by-sa,cc0,pdm","license_type":"modification","category":"sound_effect","extension":"mp3,ogg,wav"}
]
for p in tests:
 try:
  r=s.get(u,params=p,timeout=20);print("\nQUERY",p,"STATUS",r.status_code)
  d=r.json();print("COUNT",d.get("result_count"),"PAGE_COUNT",d.get("page_count"))
  for x in d.get("results",[])[:5]:
   print(json.dumps({k:x.get(k) for k in ["title","license","license_version","category","filetype","url","foreign_landing_url","tags"]},ensure_ascii=False)[:2000])
 except Exception as e:print("ERROR",repr(e))
raise SystemExit(2)
