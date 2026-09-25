from __future__ import annotations

import http.server
from pathlib import Path
import socketserver
import webbrowser

PORT = 8501
DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"


def main() -> None:
    html_file = DASHBOARD_DIR / "index.html"
    print(f"=== [BONUS B1] Khoi chay Data Observability Dashboard ===")
    print(f"File dashboard tai: {html_file}")
    
    url = f"http://localhost:{PORT}/index.html"
    print(f"Dang mo trinh duyet tai: {url}")
    webbrowser.open(html_file.as_uri())

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            print(f"Dashboard dang chay tai: {url} (Nhan Ctrl+C de dung)")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung dashboard server.")
    except Exception:
        print("Mo dashboard truc tiep thanh cong!")


if __name__ == "__main__":
    main()
