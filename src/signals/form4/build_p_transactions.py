#!/usr/bin/env python3
"""Build P-transaction table from SEC bulk Form 345 ZIPs, then detect clusters."""
import zipfile, io, csv, sqlite3, os, glob, sys, time

DB = "/tmp/form4_bulk.db"
DIR = "/tmp/f345"

def open_tsv(z, name):
    f = z.open(name)
    return csv.DictReader(io.TextIOWrapper(f, encoding='utf-8', errors='ignore'), delimiter='\t')

def getcik(s):
    s = (s or "").strip()
    return int(s) if s.isdigit() else None

def build():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS p_transactions (
        accession TEXT, company_cik INTEGER, ticker TEXT, issuer_name TEXT,
        owner_cik INTEGER, transaction_date TEXT, shares REAL, price REAL, filing_date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS q_done (qname TEXT PRIMARY KEY)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pt ON p_transactions(company_cik, transaction_date)")
    conn.commit()
    done = set(r[0] for r in c.execute("SELECT qname FROM q_done"))
    zips = sorted(glob.glob(f"{DIR}/*_form345.zip"))
    print("zips found:", len(zips), flush=True)
    for zp in zips:
        qn = os.path.basename(zp).replace("_form345.zip", "")
        if qn in done:
            print(f"skip {qn}", flush=True); continue
        t0 = time.time()
        try:
            z = zipfile.ZipFile(zp)
        except Exception as e:
            print(f"badzip {qn} {e}", flush=True); continue
        # SUBMISSION: accession -> issuer cik, ticker, filing date, doc type
        sub = {}
        for r in open_tsv(z, "SUBMISSION.tsv"):
            if r.get("DOCUMENT_TYPE") != "4":
                continue
            acc = r["ACCESSION_NUMBER"]
            sub[acc] = (getcik(r.get("ISSUERCIK")), (r.get("ISSUERTRADINGSYMBOL") or "").strip(),
                        (r.get("FILING_DATE") or "").strip(), r.get("ISSUERNAME","").strip())
        # REPORTINGOWNER: accession -> set of owner ciks
        owners = {}
        for r in open_tsv(z, "REPORTINGOWNER.tsv"):
            acc = r["ACCESSION_NUMBER"]
            if acc not in sub: continue
            oc = getcik(r.get("RPTOWNERCIK"))
            if oc is not None:
                owners.setdefault(acc, set()).add(oc)
        # NONDERIV_TRANS: filter TRANS_CODE=='P'
        rows = []
        for r in open_tsv(z, "NONDERIV_TRANS.tsv"):
            if r.get("TRANS_CODE") != "P":
                continue
            acc = r["ACCESSION_NUMBER"]
            if acc not in sub: continue
            td = (r.get("TRANS_DATE") or "").strip()
            if not td: continue
            try: sh = float(r.get("TRANS_SHARES") or 0)
            except: sh = 0.0
            try: pr = float(r.get("TRANS_PRICEPERSHARE") or 0)
            except: pr = 0.0
            ccik, tk, fd, nm = sub[acc]
            why = owners.get(acc, set())
            if not why:
                continue
            for oc in why:
                rows.append((acc, ccik, tk, nm, oc, td, sh, pr, fd))
        c.executemany("INSERT INTO p_transactions VALUES (?,?,?,?,?,?,?,?,?)", rows)
        c.execute("INSERT OR IGNORE INTO q_done VALUES (?)", (qn,))
        conn.commit()
        print(f"{qn}: form4_subs={len(sub)} P_rows={len(rows)} ({time.time()-t0:.0f}s)", flush=True)
    conn.commit(); conn.close()
    print("BUILD DONE", flush=True)

if __name__ == "__main__":
    build()
