"""
Streamlit Self‑Service Frontend (PoC)
------------------------------------
Features:
- Lightweight login gate (session-based) suitable for demos.
- Sidebar to configure API Base URL + API Key (stored only in session, not persisted).
- Form to accept Phone, Email, and Vehicle Document upload.
- Sends request to your backend API (JSON or multipart as needed) and fetches the 'user graph'.
- Visualizes the graph using PyVis inside Streamlit, shows raw JSON, and lets users download.
- Robust error handling for 4xx/5xx, timeouts, and validation.

How to run locally:
  pip install -r requirements.txt  (see requirements below)
  streamlit run app.py

Environment variables supported (optional):
  BACKEND_BASE_URL, API_KEY, DEMO_USER, DEMO_PASS

Replace the API endpoints in `API_PATHS` to match your backend.
"""

import io
import json
import os
import time
from typing import Dict, Any, List, Tuple

import requests
import streamlit as st
from pydantic import BaseModel, EmailStr, Field, validator
from pyvis.network import Network

# ---------------------------
# Config & Constants
# ---------------------------
st.set_page_config(page_title="User Graph Self‑Service", page_icon="🕸️", layout="wide")


API_PATHS = {
    "auth": "/v1/auth/login",  # POST {email, password} -> {token}
    "graph": "/v1/graph/fetch", # POST payload -> { nodes: [...], edges: [...] }
}

DEFAULTS = {
    "base_url": os.getenv("BACKEND_BASE_URL", "https://api.example.com"),
    "api_key": os.getenv("API_KEY", ""),
    "demo_user": os.getenv("DEMO_USER", "demo@example.com"),
    "demo_pass": os.getenv("DEMO_PASS", "password123"),
}

class InputPayload(BaseModel):
    phone: str = Field("", description="User's phone number")
    email: EmailStr | None = Field(None, description="User's email address")

    @validator("phone")
    def phone_must_look_valid(cls, v: str):
        p = v.strip()
        if not p:
            raise ValueError("Phone is required")
        digits = [c for c in p if c.isdigit()]
        if len(digits) < 7:
            raise ValueError("Phone looks too short")
        return p

def _headers(api_key: str | None, bearer: str | None) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["x-api-key"] = api_key
    if bearer:
        h["Authorization"] = f"Bearer {bearer}"
    return h

@st.cache_data(ttl=300, show_spinner=False)
def fetch_user_graph(
    base_url: str,
    api_key: str | None,
    bearer: str | None,
    payload: Dict[str, Any],
    vehicle_doc: bytes | None,
    filename: str | None,
    timeout: int = 20,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + API_PATHS["graph"]
    headers = _headers(api_key, bearer)

    try:
        if vehicle_doc and filename:
            files = {"vehicle_document": (filename, vehicle_doc)}
            data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in payload.items()}
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=timeout)
        else:
            resp = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=timeout)

        if resp.status_code == 200:
            return resp.json()
        else:
            try:
                problem = resp.json()
            except Exception:
                problem = {"message": resp.text}
            raise RuntimeError(f"Backend error {resp.status_code}: {problem}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error: {e}")

def build_pyvis_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    net = Network(height="650px", width="100%", directed=True, bgcolor="#ffffff")
    net.barnes_hut()

    for n in nodes:
        node_id = n.get("id") or n.get("key") or n.get("name")
        if node_id is None:
            continue
        label = n.get("label") or str(node_id)
        title_parts = [f"<b>{label}</b>"]
        for k, v in n.items():
            if k not in {"id", "key", "name", "label"}:
                title_parts.append(f"{k}: {v}")
        title = "<br/>".join(title_parts)
        net.add_node(node_id, label=label, title=title)

    for e in edges:
        src = e.get("source") or e.get("from")
        dst = e.get("target") or e.get("to")
        if src is None or dst is None:
            continue
        label = e.get("label") or e.get("relation")
        net.add_edge(src, dst, title=label, label=label)

    net.set_options(
        """
        const options = {
          physics: { stabilization: true },
          nodes: { shape: 'dot', scaling: { min: 8, max: 28 }},
          edges: { arrows: { to: {enabled: true} }, smooth: true }
        }
        """
    )
    return net.generate_html("graph.html")


def download_bytes(name: str, content: bytes, mime: str):
    st.download_button(label=f"Download {name}", data=content, file_name=name, mime=mime)

# Sidebar config
with st.sidebar:
    st.header("⚙️ Backend Settings")
    base_url = st.text_input("API Base URL", value=DEFAULTS["base_url"])
    api_key = st.text_input("API Key (if required)", type="password", value=DEFAULTS["api_key"])

    st.divider()
    demo_user = st.text_input("Demo user (email)", value=DEFAULTS["demo_user"])
    demo_pass = st.text_input("Demo password", type="password", value=DEFAULTS["demo_pass"])

if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

st.title("🕸️ User Graph Self‑Service")

# Login
if not st.session_state.auth_token:
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Login") 
        email = st.text_input("Email", value=demo_user)
        password = st.text_input("Password", type="password", value=demo_pass)
        login_btn = st.form_submit_button("Sign in")

    if login_btn:
        try:
            auth_url = base_url.rstrip("/") + API_PATHS["auth"]
            resp = requests.post(auth_url, json={"email": email, "password": password}, headers=_headers(api_key, None), timeout=20)
            if resp.status_code == 200:
                token = resp.json().get("token") or resp.json().get("access_token")
                st.session_state.auth_token = token or f"demo-{int(time.time())}"
                st.success("Logged in!")
            else:
                st.session_state.auth_token = f"demo-{int(time.time())}"
                st.warning("Auth failed, using demo token.")
        except requests.exceptions.RequestException:
            st.session_state.auth_token = f"demo-{int(time.time())}"
            st.info("Auth API not reachable, using demo token.")

# Input form
if st.session_state.auth_token:
    with st.form("input_form"):
        phone_in = st.text_input("Phone *")
        email_in = st.text_input("Email (optional)")
        uploaded = st.file_uploader("Vehicle document (optional)", type=["pdf", "jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Fetch Graph 🕸️")

    if submitted:
        try:
            payload_obj = InputPayload(phone=phone_in, email=email_in or None)
            file_bytes = uploaded.read() if uploaded else None
            filename = uploaded.name if uploaded else None
            graph_resp = fetch_user_graph(base_url, api_key, st.session_state.auth_token, payload_obj.dict(exclude_none=True), file_bytes, filename)
            st.session_state.graph_resp = graph_resp
            st.success("Graph fetched!")
        except Exception as e:
            st.error(str(e))

if st.session_state.get("graph_resp"):
    graph = st.session_state.graph_resp
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    st.subheader("Graph Overview")
    st.json(graph)

    try:
        html = build_pyvis_graph(nodes, edges)
        st.components.v1.html(html, height=680, scrolling=True)
    except Exception as e:
        st.warning(f"Could not render interactive graph: {e}")

st.caption("Built with Streamlit • Replace API_PATHS to match your backend.")
