import streamlit as st
import json, re, io, time, os

# ── Page config ──
st.set_page_config(page_title="ESC PLAN — PDF Data Extractor", page_icon="📄", layout="wide")

# ── Branding ──
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding-bottom:16px;border-bottom:1px solid #e5e7eb;margin-bottom:16px">
    <div>
        <div style="font:700 26px sans-serif;letter-spacing:.02em">ESC PLAN</div>
        <div style="font:500 14px sans-serif;color:#6b7280">PDF Data Extractor</div>
    </div>
    <div style="margin-left:auto;font:600 11px monospace;padding:4px 10px;border:1px solid #e5e7eb;border-radius:6px;color:#6b7280">v3.0</div>
</div>
""", unsafe_allow_html=True)

st.caption("Extract any data from any PDF. Upload PDFs, define what fields you need, and get structured results.")

# ── Session state ──
if "results" not in st.session_state:
    st.session_state.results = []

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Settings")

    ai_provider = st.selectbox("AI Provider", ["Google Gemini (Free)", "Anthropic Claude (Paid)"])

    if ai_provider == "Google Gemini (Free)":
        api_key = st.text_input("Gemini API Key (free)", type="password",
                                help="Get yours FREE at aistudio.google.com/apikey — no credit card needed")
        st.markdown("[🔑 Get free Gemini API key →](https://aistudio.google.com/apikey)")
    else:
        api_key = st.text_input("Anthropic API Key", type="password")

    # Check for secrets
    if not api_key:
        if ai_provider == "Google Gemini (Free)":
            api_key = os.environ.get("GEMINI_API_KEY", st.secrets.get("GEMINI_API_KEY", "")) if hasattr(st, 'secrets') else os.environ.get("GEMINI_API_KEY", "")
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY", st.secrets.get("ANTHROPIC_API_KEY", "")) if hasattr(st, 'secrets') else os.environ.get("ANTHROPIC_API_KEY", "")

    st.divider()
    st.markdown("**How to get Gemini key (FREE):**")
    st.markdown("""
    1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
    2. Sign in with Google
    3. Click **Create API Key**
    4. Copy & paste it here
    
    ✅ Free: 1,500 requests/day  
    ✅ No credit card needed
    """)
    st.divider()
    st.caption("Built by ESC PLAN")


# ── PDF text extraction ──
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
        return f"[PDF extraction error: {e}]"


# ── AI extraction ──
def build_prompt(text, title, fields, rules):
    if fields:
        field_list = "\n".join(f'  "{f}"' for f in fields)
        field_json = ",".join(f'"{f}":null' for f in fields)
        return f"""You are extracting structured data from a PDF document.

CRITICAL: Return EACH data point as a SEPARATE key in the JSON. Do NOT combine values into a single "note" or text string.

Extract these fields — each as its own separate JSON key:
{field_list}

Rules:
1. Each field is a SEPARATE JSON key. Never merge them.
2. For amounts/numbers: return as a number (no currency symbols, no commas).
3. For text/dates: return as a string.
4. null for missing values.
5. "confidence": "high" only when unambiguous.
{f"Additional instructions: {rules}" if rules else ""}

Return ONLY valid JSON (no markdown, no backticks, no explanation):
{{"rows":[{{{field_json},"found":true,"confidence":"high","note":"brief 10-word evidence"}}]}}
If the PDF has multiple entries (line items, trips, invoices), return one row per entry.

FILE: {title}

PDF TEXT:
{text[:18000]}"""
    else:
        return f"""You are extracting ALL structured data from a PDF document.

CRITICAL RULES:
1. Identify EVERY distinct data point (dates, numbers, names, references, amounts, quantities, etc.)
2. Return each as a SEPARATE key — one key per data point
3. Use SHORT, CLEAR key names like: "Invoice_Number", "Bill_Date", "Freight_Charges", "Total", etc.
4. Numbers: digits only (no currency symbols). Dates: as text. Text: as-is.
5. Do NOT combine multiple values into one key.
{f"Additional instructions: {rules}" if rules else ""}

Return ONLY valid JSON (no markdown, no backticks, no explanation):
{{"rows":[{{...each_data_point_as_separate_key...,"found":true,"confidence":"high","note":"10-word summary only"}}]}}
If the PDF has multiple entries, return one row per entry.

FILE: {title}

PDF TEXT:
{text[:18000]}"""


def call_gemini(prompt, api_key):
    """Call Google Gemini API."""
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean markdown fences
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
            return json.loads(text.strip())
    except Exception as e:
        return {"rows": [], "error": str(e)[:200]}


def call_anthropic(prompt, api_key):
    """Call Anthropic Claude API."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw)
        return json.loads(raw.strip())
    except Exception as e:
        return {"rows": [], "error": str(e)[:200]}


def extract_from_pdf(text, title, fields, rules, api_key, provider):
    prompt = build_prompt(text, title, fields, rules)
    if "Gemini" in provider:
        return call_gemini(prompt, api_key)
    else:
        return call_anthropic(prompt, api_key)


# ═══════════════════════════════════════════════════
# MAIN UI
# ═══════════════════════════════════════════════════

# Step 1: Fields
st.markdown("### 📋 What data do you want from the PDFs?")
field_text = st.text_area(
    "fields",
    placeholder="e.g. Invoice Number, Invoice Date, Transporter Name, Freight Charges, Unloading Charges, Total Amount\n\nLeave blank to auto-detect everything.",
    height=80,
    label_visibility="collapsed"
)
fields = [f.strip() for f in re.split(r"[,;\n]+", field_text) if f.strip()] if field_text.strip() else []

if fields:
    st.caption(f"**{len(fields)} fields:** {', '.join(fields)}")
else:
    st.caption("No fields specified — will auto-detect all data points from the PDFs")

# Rules
with st.expander("📝 Extraction instructions (optional)", expanded=False):
    rules = st.text_area(
        "rules",
        placeholder="e.g.\n• Disha Trans: Freight | Un-Ldg | Un-Ldg Deten | Other | Total\n• Match rows by LR number\n• Detention without stated point: use dates to determine loading vs unloading",
        height=100,
        label_visibility="collapsed"
    )

# Step 2: Upload
st.markdown("### 📁 Upload PDFs")
uploaded_files = st.file_uploader("upload", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} PDF(s) ready")

# Step 3: Extract
if uploaded_files and st.button("🚀 Start Extraction", type="primary", disabled=not api_key):
    if not api_key:
        st.error("Enter your API key in the sidebar")
        st.stop()

    all_results = []
    progress = st.progress(0)
    status = st.empty()
    stats_box = st.empty()
    stats = {"extracted": 0, "failed": 0}

    for i, pdf_file in enumerate(uploaded_files):
        status.text(f"[{i+1}/{len(uploaded_files)}] Processing {pdf_file.name}...")
        progress.progress((i + 1) / len(uploaded_files))

        pdf_bytes = pdf_file.read()
        text = extract_pdf_text(pdf_bytes)

        if len(text.replace(" ", "")) < 20:
            all_results.append({"source": pdf_file.name, "status": "FAILED", "error": "No text extracted", "data": {}})
            stats["failed"] += 1
            continue

        result = extract_from_pdf(text, pdf_file.name, fields, rules, api_key, ai_provider)

        if result.get("error"):
            all_results.append({"source": pdf_file.name, "status": "ERROR", "error": result["error"], "data": {}})
            stats["failed"] += 1
        else:
            for row in result.get("rows", []):
                skip = {"r", "found", "confidence", "note"}
                data = {k: v for k, v in row.items() if k.lower() not in skip}
                all_results.append({
                    "source": pdf_file.name, "status": "EXTRACTED",
                    "note": row.get("note", ""), "data": data
                })
                stats["extracted"] += 1

        stats_box.markdown(f"✅ Extracted: **{stats['extracted']}** | ❌ Failed: **{stats['failed']}**")
        time.sleep(0.3)

    progress.progress(1.0)
    status.text("✅ Done!")
    st.session_state.results = all_results

# ── Results ──
if st.session_state.results:
    st.markdown("### 📊 Results")
    results = st.session_state.results

    # Discover all columns
    all_cols = []
    for r in results:
        for k in r["data"].keys():
            if not any(c.lower() == k.lower() for c in all_cols):
                all_cols.append(k)

    # Build table
    table_data = []
    for r in results:
        row = {"Source PDF": r["source"], "Status": r["status"]}
        for col in all_cols:
            val = None
            for k, v in r["data"].items():
                if k.lower() == col.lower():
                    val = v
                    break
            row[col] = val if val is not None else ""
        row["Note"] = r.get("note", r.get("error", ""))
        table_data.append(row)

    st.dataframe(table_data, use_container_width=True, height=400)

    # Downloads
    col1, col2 = st.columns(2)

    import csv
    csv_buf = io.StringIO()
    if table_data:
        writer = csv.DictWriter(csv_buf, fieldnames=table_data[0].keys())
        writer.writeheader()
        writer.writerows(table_data)
    col1.download_button("📥 Download CSV", csv_buf.getvalue(),
                         file_name="pdf_extract_results.csv", mime="text/csv")
    col2.download_button("📥 Download JSON", json.dumps(table_data, indent=2, ensure_ascii=False),
                         file_name="pdf_extract_results.json", mime="application/json")
