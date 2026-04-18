import csv, os
from collections import Counter

csv_path = os.path.join(os.path.dirname(__file__), "diagnostic_results.csv")
with open(csv_path, "r", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))

counts = Counter(r["status"] for r in reader)
print("=== SONUCLAR (472 dosya) ===")
for status, count in counts.most_common():
    pct = count / len(reader) * 100
    print(f"  {status:20s} {count:4d} ({pct:5.1f}%)")

print()
print("=== NO_DATA DOSYALAR ===")
fails = [r for r in reader if r["status"] == "NO_DATA"]
for r in fails:
    print(f"  {r['dir']}/{r['file']}")

print()
print("=== DATA_ONLY (veri var, property yok) ===")
data_only = [r for r in reader if r["status"] == "DATA_ONLY"]
for r in data_only:
    print(f"  {r['dir']}/{r['file']} ({r['n_points']} pts)")

print()
print("=== Sifir/Negatif E degerleri ===")
bad_e = [r for r in reader if r["E_gpa"] and float(r["E_gpa"]) <= 5 and r["status"] == "FULL_RESULT"]
print(f"  {len(bad_e)} dosyada E <= 5 GPa")
for r in bad_e[:10]:
    print(f"    {r['dir']}/{r['file']}: E={r['E_gpa']}")

print()
print("=== Asiri yuksek UTS (>2000 MPa, spheci) ===")
hi_uts = [r for r in reader if r["uts_mpa"] and float(r["uts_mpa"]) > 2000]
print(f"  {len(hi_uts)} dosyada UTS > 2000 MPa")
for r in hi_uts[:10]:
    print(f"    {r['dir']}/{r['file']}: UTS={r['uts_mpa']}")
