# 🕸️ User Graph Self‑Service Frontend

This is a **Streamlit-based frontend** that lets customers log in, provide identifiers (phone, email, vehicle documents), and fetch their **user graph** from a backend API. The app visualizes the graph interactively and allows raw JSON/CSV export.

## 🚀 Features
- Login with backend credentials (or demo fallback)
- Input phone/email and upload vehicle document
- Calls your backend API to fetch `{ nodes, edges }`
- Interactive graph visualization using PyVis
- Download JSON + CSV of graph data
- Ready to deploy on **Streamlit Cloud**

## 🛠️ Setup

### 1. Clone repo
```bash
git clone https://github.com/YOUR-USERNAME/user-graph-frontend.git
cd user-graph-frontend
```

### 2. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run locally
```bash
export BACKEND_BASE_URL="https://api.your-backend.com"
export API_KEY="your-api-key-if-any"
export DEMO_USER="demo@example.com"
export DEMO_PASS="password123"

streamlit run app.py
```

### 4. Deploy to Streamlit Cloud
1. Push this repo to GitHub.
2. Go to [Streamlit Cloud](https://share.streamlit.io) → **New App**.
3. Select repo & branch, set **app.py** as entrypoint.
4. Add these in **Secrets** (Settings → Secrets):
   ```toml
   BACKEND_BASE_URL="https://api.your-backend.com"
   API_KEY="your-api-key"
   DEMO_USER="demo@example.com"
   DEMO_PASS="password123"
   ```
5. Deploy 🚀

---
Built with ❤️ using [Streamlit](https://streamlit.io).
