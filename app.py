import streamlit as st
import json, re, io, time, os

st.set_page_config(page_title="ESC PLAN — PDF Data Extractor", page_icon="📄", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.block-container {max-width: 1100px; padding-top: 2rem;}
.brand-header {
    display: flex; align-items: center; gap: 20px; padding: 20px 28px;
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
    border-radius: 16px; margin-bottom: 24px; color: white; position: relative; overflow: hidden;
}
.brand-header::before {
    content: ''; position: absolute; top: -50%; right: -20%; width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(251,191,36,0.15) 0%, transparent 70%); border-radius: 50%;
}
.brand-name { font: 800 32px 'Inter', sans-serif; letter-spacing: .04em; }
.brand-sub { font: 500 14px 'Inter', sans-serif; opacity: 0.7; margin-top: 2px; }
.brand-badge {
    position: absolute; right: 24px; top: 50%; transform: translateY(-50%);
    font: 600 11px monospace; padding: 4px 12px; border: 1px solid rgba(255,255,255,0.3);
    border-radius: 6px; color: rgba(255,255,255,0.7);
}
.ui-card {
    background: white; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 24px; margin-bottom: 16px; transition: box-shadow 0.2s;
}
.ui-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.ui-card h3 { font: 700 16px 'Inter', sans-serif; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
.ui-card .desc { font-size: 13px; color: #6b7280; margin-bottom: 14px; }
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }
.stat-box {
    background: white; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 16px; text-align: center; transition: transform 0.2s;
}
.stat-box:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.stat-num { font: 700 28px 'Inter', sans-serif; }
.stat-label { font: 500 11px 'Inter', sans-serif; text-transform: uppercase; letter-spacing: 0.1em; color: #6b7280; margin-top: 4px; }
.stat-extracted .stat-num { color: #4f46e5; }
.stat-ok .stat-num { color: #059669; }
.stat-failed .stat-num { color: #dc2626; }
.stat-total .stat-num { color: #1e1b4b; }
[data-testid="stFileUploader"] { border: 2px dashed #d1d5db !important; border-radius: 14px !important; padding: 8px !important; }
[data-testid="stFileUploader"]:hover { border-color: #4f46e5 !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important; border-radius: 10px !important; padding: 12px 28px !important;
    font-weight: 600 !important; transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(79,70,229,0.35) !important; }
.stProgress > div > div { background: linear-gradient(90deg, #4f46e5, #7c3aed) !important; border-radius: 4px !important; }
[data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden; }
.stDownloadButton > button { border-radius: 10px !important; border: 1px solid #e5e7eb !important; font-weight: 600 !important; }
.stDownloadButton > button:hover { border-color: #4f46e5 !important; color: #4f46e5 !important; }
@media (prefers-color-scheme: dark) {
    .ui-card { background: #1f2937; border-color: #374151; }
    .stat-box { background: #1f2937; border-color: #374151; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-name">ESC PLAN</div>
        <div class="brand-sub">PDF Data Extractor — Extract any data from any PDF</div>
    </div>
    <div class="brand-badge">v4.0</div>
</div>
""", unsafe_allow_html=True)

if "results" not in st.session_state:
    st.session_state.results = []
if "field_text" not in st.session_state:
    st.session_state.field_text = ""

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

# ── Sidebar ──
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    # Groq keys
    groq_keys = []
    gk = get_secret("GROQ_API_KEY")
    if gk: groq_keys.append(gk)
    for i in range(2, 6):
        gk = get_secret(f"GROQ_API_KEY_{i}")
        if gk: groq_keys.append(gk)

    # Gemini keys
    gemini_keys = []
    gk = get_secret("GEMINI_API_KEY")
    if gk: gemini_keys.append(gk)
    for i in range(2, 6):
        gk = get_secret(f"GEMINI_API_KEY_{i}")
        if gk: gemini_keys.append(gk)

    has_saved_keys = len(groq_keys) + len(gemini_keys) > 0

    if has_saved_keys:
        if groq_keys:
            st.success(f"⚡ {len(groq_keys)} Groq key(s) — ultra fast")
        if gemini_keys:
            st.info(f"🔄 {len(gemini_keys)} Gemini key(s) — backup")
        api_key = groq_keys[0] if groq_keys else gemini_keys[0]
        sidebar_key = ""
    else:
        provider = st.selectbox("AI Provider", ["Groq (Fast & Free)", "Google Gemini (Free)"])
        api_key = st.text_input("API Key", type="password")
        sidebar_key = api_key
        if "Groq" in provider:
            st.markdown("[Get free Groq key →](https://console.groq.com)")
        else:
            st.markdown("[Get free Gemini key →](https://aistudio.google.com/apikey)")

    st.divider()
    st.markdown("#### 📖 Quick Guide")
    st.markdown("""
    <div style="font-size:13px; line-height:1.8">
    <b>Step 1:</b> Define fields you want<br>
    <b>Step 2:</b> Upload your PDFs<br>
    <b>Step 3:</b> Click Extract → Done!<br><br>
    💡 <b>Tip:</b> Leave fields blank to auto-detect
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown("""
    <div style="text-align:center;padding:8px;font-size:12px;color:#9ca3af">
    <b>ESC PLAN</b><br>Powered by Groq + Gemini AI<br>Free • Fast • No signup
    </div>
    """, unsafe_allow_html=True)


# ── Templates ──
TEMPLATES = {
    "🚛 Freight Invoice": "Invoice Number, Invoice Date, Bill Date, Transporter Name, Vehicle Number, LR Number, Freight Charges, Unloading Charges, Detention Loading, Detention Unloading, Other Charges, Total Amount",
    "🧾 Purchase Invoice": "Invoice Number, Invoice Date, Vendor Name, Item Description, Quantity, Unit Price, GST Amount, Total Amount",
    "💰 Expense Receipt": "Receipt Date, Merchant Name, Category, Amount, Payment Method",
    "📋 Custom (blank)": "",
}


def extract_pdf_text(pdf_bytes):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n--- Page Break ---\n\n".join(pages)
    except Exception as e:
        return f"[Error: {e}]"


def build_prompt(text, title, fields, rules):
    if fields:
        field_list = "\n".join(f'  "{f}"' for f in fields)
        field_json = ",".join(f'"{f}":null' for f in fields)
        return f"""You are extracting structured data from a PDF document.

CRITICAL: Return EACH data point as a SEPARATE key in the JSON.

Extract these fields — each as its own separate JSON key:
{field_list}

Rules:
1. Each field is a SEPARATE JSON key. Never merge them.
2. For amounts/numbers: return as a number (no currency symbols, no commas).
3. For text/dates: return as a string.
4. null for missing values.
{f"Additional instructions: {rules}" if rules else ""}

Return ONLY valid JSON:
{{"rows":[{{{field_json},"found":true,"confidence":"high","note":"brief 10-word evidence"}}]}}
If the PDF has multiple entries, return one row per entry.

FILE: {title}

PDF TEXT:
{text[:15000]}"""
    else:
        return f"""Extract ALL structured data from this PDF.

Rules:
1. Each data point as a SEPARATE JSON key
2. Use clear key names: "Invoice_Number", "Bill_Date", "Freight_Charges", etc.
3. Numbers: digits only. Dates: as text. Text: as-is.
4. Do NOT combine values into one key.
{f"Additional instructions: {rules}" if rules else ""}

Return ONLY valid JSON:
{{"rows":[{{...each_data_point_as_separate_key...,"found":true,"confidence":"high","note":"10-word summary"}}]}}
If multiple entries, return one row per entry.

FILE: {title}

PDF TEXT:
{text[:15000]}"""


# ── Groq API call (ultra fast) ──
def call_groq(prompt, key):
    import urllib.request
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"]
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw).strip()
        return json.loads(raw)


# ── Gemini API call (backup) ──
def call_gemini(prompt, key):
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-3.6-flash")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.1, max_output_tokens=4000)
    )
    raw = response.text
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw).strip()
    return json.loads(raw)


# ── Smart caller with key rotation ──
def call_ai(prompt, sidebar_key=""):
    # Try Groq first (fastest)
    for key in groq_keys:
        try:
            return call_groq(prompt, key)
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                continue
            elif "JSON" in err or "json" in err:
                return {"rows": [], "error": f"Invalid JSON from Groq"}
            else:
                continue

    # Then Gemini
    for key in gemini_keys:
        try:
            return call_gemini(prompt, key)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                continue
            elif "JSON" in err or "json" in err:
                return {"rows": [], "error": f"Invalid JSON from Gemini"}
            else:
                continue

    # Sidebar key as last resort
    if sidebar_key:
        try:
            if sidebar_key.startswith("gsk_"):
                return call_groq(prompt, sidebar_key)
            else:
                return call_gemini(prompt, sidebar_key)
        except Exception as e:
            return {"rows": [], "error": str(e)[:200]}

    return {"rows": [], "error": "All API keys failed. Wait a minute and retry."}


# ═══════════════════════════════════════════════════
# MAIN UI
# ═══════════════════════════════════════════════════

st.markdown("""
<div class="ui-card">
    <h3>📋 Step 1 — Define Your Fields</h3>
    <div class="desc">Pick a template or type your own. Each field becomes a separate column.</div>
</div>
""", unsafe_allow_html=True)

template_cols = st.columns(len(TEMPLATES))
for i, (name, val) in enumerate(TEMPLATES.items()):
    with template_cols[i]:
        if st.button(name, use_container_width=True, key=f"tmpl_{i}"):
            st.session_state.field_text = val
            st.rerun()

field_text = st.text_area(
    "fields", value=st.session_state.field_text,
    placeholder="e.g. Invoice Number, Invoice Date, Vendor Name, Amount, Tax, Total\n\nLeave blank to auto-detect everything.",
    height=80, key="field_input", label_visibility="collapsed"
)
st.session_state.field_text = field_text

fields = [f.strip() for f in re.split(r"[,;\n]+", field_text) if f.strip()] if field_text.strip() else []
if fields:
    st.caption(f"✅ **{len(fields)} fields:** {', '.join(fields)}")
else:
    st.info("💡 No fields specified — will auto-detect all data points")

with st.expander("📝 Extraction instructions (optional)"):
    rules = st.text_area("rules", placeholder="Special rules for your PDF format...", height=80, label_visibility="collapsed")

st.markdown("---")

st.markdown("""
<div class="ui-card">
    <h3>📁 Step 2 — Upload Your PDFs</h3>
    <div class="desc">Drag and drop PDFs. Each is processed separately.</div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Upload", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    c1, c2 = st.columns([3, 1])
    with c1: st.success(f"✅ **{len(uploaded_files)} PDF(s)** ready")
    with c2: st.caption(f"Total: {sum(f.size for f in uploaded_files)/(1024*1024):.1f} MB")

st.markdown("---")

st.markdown("""
<div class="ui-card">
    <h3>🚀 Step 3 — Extract Data</h3>
    <div class="desc">Click to start. Groq processes each PDF in ~2 seconds.</div>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1, 3])
with c1:
    extract_btn = st.button("🚀 Start Extraction", type="primary",
                            disabled=not ((api_key or groq_keys or gemini_keys) and uploaded_files),
                            use_container_width=True)
with c2:
    if not (api_key or groq_keys or gemini_keys):
        st.warning("⚠️ Add an API key in the sidebar")
    elif not uploaded_files:
        st.info("📁 Upload PDFs above")
    else:
        total_keys = len(groq_keys) + len(gemini_keys) + (1 if sidebar_key else 0)
        engine = "⚡ Groq" if groq_keys else "🔄 Gemini"
        st.success(f"✅ Ready! {engine} with {total_keys} key(s)")

if extract_btn and uploaded_files:
    all_results = []
    progress = st.progress(0)
    status_text = st.empty()
    stats_display = st.empty()
    live_log = st.empty()
    stats = {"extracted": 0, "failed": 0}
    log_messages = []
    start_time = time.time()

    for i, pdf_file in enumerate(uploaded_files):
        t0 = time.time()
        progress.progress((i + 1) / len(uploaded_files))
        status_text.markdown(f"**Processing [{i+1}/{len(uploaded_files)}]:** `{pdf_file.name}`")

        pdf_bytes = pdf_file.read()
        text = extract_pdf_text(pdf_bytes)

        if len(text.replace(" ", "")) < 20:
            all_results.append({"source": pdf_file.name, "status": "FAILED", "error": "No text extracted", "data": {}})
            stats["failed"] += 1
            log_messages.append(f"❌ {pdf_file.name} — no text")
        else:
            result = call_ai(build_prompt(text, pdf_file.name, fields, rules), sidebar_key if not has_saved_keys else "")

            if result.get("error"):
                all_results.append({"source": pdf_file.name, "status": "ERROR", "error": result["error"], "data": {}})
                stats["failed"] += 1
                log_messages.append(f"⚠️ {pdf_file.name} — {result['error'][:50]}")
            else:
                row_count = 0
                for row in result.get("rows", []):
                    skip = {"r", "found", "confidence", "note"}
                    data = {k: v for k, v in row.items() if k.lower() not in skip}
                    all_results.append({
                        "source": pdf_file.name, "status": "EXTRACTED",
                        "note": row.get("note", ""), "data": data
                    })
                    row_count += 1
                stats["extracted"] += row_count
                elapsed = time.time() - t0
                log_messages.append(f"✅ {pdf_file.name} — {row_count} row(s) in {elapsed:.1f}s")

        stats_display.markdown(f"""
        <div class="stat-grid">
            <div class="stat-box stat-total"><div class="stat-num">{i+1}/{len(uploaded_files)}</div><div class="stat-label">PDFs Done</div></div>
            <div class="stat-box stat-extracted"><div class="stat-num">{stats['extracted']}</div><div class="stat-label">Rows Extracted</div></div>
            <div class="stat-box stat-ok"><div class="stat-num">{stats['extracted']}</div><div class="stat-label">Successful</div></div>
            <div class="stat-box stat-failed"><div class="stat-num">{stats['failed']}</div><div class="stat-label">Failed</div></div>
        </div>
        """, unsafe_allow_html=True)
        live_log.code("\n".join(log_messages[-8:]), language=None)
        time.sleep(0.2)

    total_time = time.time() - start_time
    progress.progress(1.0)
    status_text.markdown(f"### ✅ Done in {total_time:.1f} seconds!")
    st.session_state.results = all_results
    st.balloons()

# ═══ RESULTS ═══
if st.session_state.results:
    st.markdown("---")
    st.markdown("""<div class="ui-card"><h3>📊 Results</h3><div class="desc">Download as CSV, JSON, or Excel.</div></div>""", unsafe_allow_html=True)

    results = st.session_state.results
    all_cols = []
    for r in results:
        for k in r["data"].keys():
            if not any(c.lower() == k.lower() for c in all_cols):
                all_cols.append(k)

    table_data = []
    for r in results:
        row = {"Source PDF": r["source"], "Status": r["status"]}
        for col in all_cols:
            val = None
            for k, v in r["data"].items():
                if k.lower() == col.lower():
                    val = v; break
            row[col] = val if val is not None else ""
        row["Note"] = r.get("note", r.get("error", ""))
        table_data.append(row)

    extracted = sum(1 for r in results if r["status"] == "EXTRACTED")
    failed = sum(1 for r in results if r["status"] in ("FAILED", "ERROR"))
    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-box stat-total"><div class="stat-num">{len(results)}</div><div class="stat-label">Total Rows</div></div>
        <div class="stat-box stat-extracted"><div class="stat-num">{extracted}</div><div class="stat-label">Extracted</div></div>
        <div class="stat-box stat-failed"><div class="stat-num">{failed}</div><div class="stat-label">Failed</div></div>
        <div class="stat-box stat-ok"><div class="stat-num">{len(all_cols)}</div><div class="stat-label">Columns</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Table View", "📄 Raw Data"])
    with tab1: st.dataframe(table_data, use_container_width=True, height=450)
    with tab2: st.json(table_data[:20])

    st.markdown("#### 📥 Download Results")
    c1, c2, c3 = st.columns(3)
    import csv
    csv_buf = io.StringIO()
    if table_data:
        writer = csv.DictWriter(csv_buf, fieldnames=table_data[0].keys())
        writer.writeheader()
        writer.writerows(table_data)
    with c1: st.download_button("📥 CSV", csv_buf.getvalue(), file_name="esc_plan_extract.csv", mime="text/csv", use_container_width=True)
    with c2: st.download_button("📥 JSON", json.dumps(table_data, indent=2, ensure_ascii=False), file_name="esc_plan_extract.json", mime="application/json", use_container_width=True)
    with c3:
        try:
            import openpyxl
            from openpyxl.styles import PatternFill, Font
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Extracted Data"
            headers = list(table_data[0].keys()) if table_data else []
            ws.append(headers)
            for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="4F46E5")
            for row in table_data: ws.append([row.get(h, "") for h in headers])
            buf = io.BytesIO(); wb.save(buf)
            st.download_button("📥 Excel", buf.getvalue(), file_name="esc_plan_extract.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        except: st.button("📥 Excel", disabled=True, use_container_width=True)

    if st.button("🗑️ Clear results & start over"):
        st.session_state.results = []; st.rerun()
