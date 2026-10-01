"""Le cabecalho e primeiras linhas de um .xlsx sem dependencias (zipfile + xml).
Uso: python xlsx_resumo.py arquivo.xlsx [n_linhas]
"""
import sys, zipfile, re, xml.etree.ElementTree as ET
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
z = zipfile.ZipFile(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
ss = []
if "xl/sharedStrings.xml" in z.namelist():
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
        ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
wb = ET.fromstring(z.read("xl/workbook.xml"))
nomes = [s.get("name") for s in wb.find("m:sheets", NS)]
sheets = sorted([f for f in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", f)], key=lambda x: int(re.findall(r"\d+", x)[0]))
for nome, f in zip(nomes, sheets):
    root = ET.fromstring(z.read(f))
    rows = root.find("m:sheetData", NS).findall("m:row", NS)
    print(f"=== aba '{nome}' ({len(rows)} linhas)")
    for row in rows[:n]:
        vals = []
        for cel in row.findall("m:c", NS):
            v = cel.find("m:v", NS); t = cel.get("t")
            if t == "s" and v is not None: vals.append(ss[int(v.text)])
            elif t == "inlineStr": vals.append("".join(x.text or "" for x in cel.iter("{%s}t" % NS["m"])))
            else: vals.append(v.text if v is not None else "")
        print(" | ".join(vals)[:600])
