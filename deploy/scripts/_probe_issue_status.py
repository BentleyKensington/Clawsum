import json, collections, urllib.request
url = "http://127.0.0.1:3100/api/companies/97112442-5ced-44f2-afb8-dd5ee90145b9/issues?limit=100"
rows = json.load(urllib.request.urlopen(url))
print("status", dict(collections.Counter(r.get("status") for r in rows)))
print("priority", dict(collections.Counter(r.get("priority") for r in rows)))
for r in rows[:12]:
    print(r.get("identifier"), r.get("status"), r.get("priority"), (r.get("title") or "")[:60])
