import hashlib
import hmac
import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
COOKIE_NAME = "sfag_auth"
COOKIE_MAX_AGE = 315_360_000  # 10 years


def _auth_token() -> str:
    """HMAC token derived from the password — changing password invalidates all cookies."""
    key = hashlib.sha256(APP_PASSWORD.encode()).digest()
    return hmac.new(key, b"authenticated", hashlib.sha256).hexdigest()


def is_authenticated(request: Request) -> bool:
    if not APP_PASSWORD:
        return True
    return request.cookies.get(COOKIE_NAME) == _auth_token()


def _login_page(error: bool = False) -> str:
    error_html = (
        '<div class="error">Incorrect password — please try again.</div>'
        if error else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Frame Art Gallery</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #070714;
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      color: white;
    }}

    .card {{
      background: #1a1a2e;
      border: 1px solid #2a2a4e;
      border-radius: 20px;
      padding: 2.5rem 2rem;
      width: min(380px, 92vw);
      box-shadow: 0 32px 80px rgba(0, 0, 0, 0.6);
    }}

    .brand {{
      text-align: center;
      margin-bottom: 2rem;
    }}

    .brand-mark {{
      width: 56px;
      height: 56px;
      background: linear-gradient(135deg, #2a2a4e, #3a3a6e);
      border: 1px solid #4a90d9;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1rem;
    }}

    .brand-mark svg {{
      width: 28px;
      height: 28px;
      stroke: #4a90d9;
      fill: none;
      stroke-width: 1.5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}

    .brand h1 {{
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: #f0f0ff;
    }}

    .brand p {{
      font-size: 0.82rem;
      color: #555577;
      margin-top: 0.3rem;
    }}

    .error {{
      background: rgba(220, 60, 60, 0.12);
      border: 1px solid rgba(220, 60, 60, 0.35);
      border-radius: 10px;
      color: #ff7070;
      font-size: 0.82rem;
      padding: 0.65rem 0.9rem;
      margin-bottom: 1rem;
      text-align: center;
    }}

    label {{
      display: block;
      font-size: 0.78rem;
      font-weight: 500;
      color: #7777aa;
      margin-bottom: 0.4rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    input[type="password"] {{
      width: 100%;
      padding: 0.8rem 1rem;
      background: #12121f;
      border: 1px solid #2a2a4e;
      border-radius: 10px;
      color: white;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      {"border-color: rgba(220,60,60,0.5);" if error else ""}
    }}

    input[type="password"]::placeholder {{
      color: #33334a;
    }}

    input[type="password"]:focus {{
      border-color: #4a90d9;
      box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.15);
    }}

    button {{
      width: 100%;
      padding: 0.85rem;
      background: #4a90d9;
      border: none;
      border-radius: 10px;
      color: white;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      margin-top: 0.75rem;
      letter-spacing: 0.01em;
      transition: background 0.2s, transform 0.1s;
    }}

    button:hover  {{ background: #5a9fe9; }}
    button:active {{ transform: scale(0.98); }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">
      <div class="brand-mark">
        <svg viewBox="0 0 24 24">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
          <rect x="5" y="6" width="14" height="8" rx="1"/>
        </svg>
      </div>
      <h1>Frame Art Gallery</h1>
      <p>Enter your password to continue</p>
    </div>

    {error_html}

    <form method="POST" action="/login">
      <label for="pw">Password</label>
      <input
        id="pw"
        type="password"
        name="password"
        placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
        autofocus
        autocomplete="current-password"
        required
      />
      <button type="submit">Unlock</button>
    </form>
  </div>
</body>
</html>"""


router = APIRouter()


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(_login_page())


@router.post("/login", include_in_schema=False)
async def login_submit(password: str = Form(...)):
    if APP_PASSWORD and password == APP_PASSWORD:
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            COOKIE_NAME,
            _auth_token(),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="strict",
        )
        return response
    return HTMLResponse(_login_page(error=True), status_code=401)
