import fsspec, pyarrow.parquet as pq, json, sys
fs = fsspec.filesystem('https')
base = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{}.parquet"
months = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
rows, prev = [], None
for mo in months:
    try:
        s = pq.read_schema(fs.open(base.format(mo)))
        names = [f.name for f in s]
    except Exception as e:
        print(f"{mo}: 取不到 ({type(e).__name__})"); continue
    if prev is not None:
        added = [n for n in names if n not in prev]
        removed = [n for n in prev if n not in names]
        renamed = [(r, a) for r in removed for a in added if r.lower() == a.lower()]
        if added or removed:
            rows.append({"month": mo, "added": added, "removed": removed,
                         "case_rename": [f"{r}->{a}" for r, a in renamed]})
            print(f"{mo}: +{added} -{removed} 大小寫改名={[f'{r}->{a}' for r,a in renamed]}")
    prev = names
print("\n=== 漂移事件總數:", len(rows), "===")
json.dump(rows, open("tlc-drift-events.json", "w"), indent=2)
