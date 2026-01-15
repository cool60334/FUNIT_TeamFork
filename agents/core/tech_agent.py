import subprocess
import sys
import os
import importlib.metadata
import time
from pathlib import Path
from typing import Dict, Any, List

from agents.base_agent import BaseAgent

try:
    from dotenv import dotenv_values
except Exception:
    dotenv_values = None

class TechAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="TechAgent", role="Environment Deployment Engineer")
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.env_path = self.project_root / ".env"
        self.brand_name = os.getenv("BRAND_NAME", "FUNIT")

    def run(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Checks environment (Python packages and System tools).
        """
        self.log_activity("Starting environment check...")

        checks: Dict[str, Any] = {}

        checks["python_version"] = self._check_python_version()
        checks["packages"] = self._check_packages()
        checks["env_file"] = self._check_env_file()
        checks["directories"] = self._check_directories()
        checks["ffmpeg"] = self._check_ffmpeg_status()
        checks["wordpress_connection"] = self._test_wordpress()
        checks["woocommerce_connection"] = self._test_woocommerce()
        checks["gemini_api"] = self._test_gemini()
        checks["lancedb"] = self._test_lancedb()

        summary = self._summarize_checks(checks)
        recommendations = self._generate_recommendations(checks)
        next_steps = self._generate_next_steps(summary)

        return {
            "status": summary["status"],
            "checks": checks,
            "summary": summary["summary"],
            "recommendations": recommendations,
            "next_steps": next_steps
        }

    def _check_python_version(self) -> Dict[str, Any]:
        """Checks Python version and virtual environment."""
        version_info = sys.version_info
        version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        venv_active = sys.prefix != sys.base_prefix

        status = "ok" if (version_info.major > 3 or (version_info.major == 3 and version_info.minor >= 10)) else "error"
        message = "Python version is compatible" if status == "ok" else "Python 版本需 >= 3.10"

        if not venv_active:
            message += " (not in venv)"

        return {
            "status": status,
            "version": version_str,
            "virtual_env": venv_active,
            "message": message
        }

    def _check_packages(self) -> Dict[str, Any]:
        """Checks required and optional packages using importlib.metadata."""
        critical_packages = [
            "pydantic",
            "pydantic-settings",
            "python-dotenv",
            "lancedb",
            "pyarrow",
            "google-generativeai",
            "sentence-transformers",
            "requests",
            "beautifulsoup4",
            "Pillow"
        ]
        optional_packages = [
            # "openai-whisper", removed - YouTube transcription no longer needed
            "crawl4ai",
            # "yt-dlp", removed - YouTube download no longer needed
            "ddgs",
            "pdfplumber",
            "google-genai",
            "fastapi",
            "uvicorn"
        ]

        missing_critical = self._find_missing_packages(critical_packages)
        missing_optional = self._find_missing_packages(optional_packages)
        installed = [p for p in critical_packages + optional_packages if p not in missing_critical + missing_optional]

        if missing_critical:
            status = "error"
            message = f"Missing critical packages: {', '.join(missing_critical)}"
        elif missing_optional:
            status = "warning"
            message = f"Missing optional packages: {', '.join(missing_optional)}"
        else:
            status = "ok"
            message = "All required packages installed"

        return {
            "status": status,
            "installed": installed,
            "missing_critical": missing_critical,
            "missing_optional": missing_optional,
            "message": message
        }

    def _find_missing_packages(self, packages: List[str]) -> List[str]:
        missing = []
        for package in packages:
            try:
                importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                missing.append(package)
            except Exception as e:
                self.log_activity(f"Error checking package {package}: {e}")
                missing.append(package)
        return missing

    def _load_env_values(self) -> Dict[str, str]:
        env_values: Dict[str, str] = {}
        if self.env_path.exists():
            if dotenv_values:
                env_values = {k: v for k, v in dotenv_values(str(self.env_path)).items() if v is not None}
            else:
                for line in self.env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    env_values[key.strip()] = value.strip()
        return {**env_values, **os.environ}

    def _check_env_file(self) -> Dict[str, Any]:
        """Checks .env file and required variables."""
        if not self.env_path.exists():
            return {
                "status": "error",
                "found": False,
                "missing_variables": [],
                "message": ".env not found"
            }

        effective_env = self._load_env_values()

        required_vars = [
            "WP_SITE_URL",
            "WP_USERNAME",
            "WP_APP_PASSWORD",
            "GEMINI_API_KEY"
        ]
        recommended_vars = [
            "HUGGINGFACE_API_KEY"
        ]
        optional_vars = [
            "LANCEDB_PATH",
            "WOOCOMMERCE_CONSUMER_KEY",
            "WOOCOMMERCE_CONSUMER_SECRET"
        ]

        missing_required = [k for k in required_vars if not effective_env.get(k)]
        missing_recommended = [k for k in recommended_vars if not effective_env.get(k)]
        missing_optional = [k for k in optional_vars if not effective_env.get(k)]

        if missing_required:
            status = "error"
            message = f"Missing required vars: {', '.join(missing_required)}"
        elif missing_recommended:
            status = "warning"
            message = f"Missing recommended vars: {', '.join(missing_recommended)}"
        else:
            status = "ok"
            message = "All required environment variables present"

        return {
            "status": status,
            "found": True,
            "missing_variables": missing_required + missing_recommended,
            "missing_optional": missing_optional,
            "message": message
        }

    def _check_directories(self) -> Dict[str, Any]:
        """Checks required directories and write access."""
        required_dirs = [
            self.project_root / "data" / "lancedb",
            self.project_root / "outputs" / self.brand_name / "收集到的資料",
            self.project_root / "outputs" / self.brand_name / "briefs",
            self.project_root / "outputs" / self.brand_name / "drafts",
            self.project_root / "outputs" / self.brand_name / "optimized",
            self.project_root / "outputs" / self.brand_name / "final",
            self.project_root / "outputs" / self.brand_name / "images",
            self.project_root / "outputs" / self.brand_name / "reports",
            self.project_root / "outputs" / self.brand_name / "strategies"
        ]

        existing = []
        missing = []
        not_writable = []

        for path in required_dirs:
            if path.exists():
                existing.append(str(path))
                if not os.access(path, os.W_OK):
                    not_writable.append(str(path))
            else:
                missing.append(str(path))

        if missing or not_writable:
            status = "warning"
            message = "Missing or non-writable directories"
        else:
            status = "ok"
            message = "All required directories present and writable"

        return {
            "status": status,
            "existing": existing,
            "missing": missing,
            "not_writable": not_writable,
            "message": message
        }

    def _check_ffmpeg(self) -> bool:
        """Checks if FFmpeg is installed and accessible."""
        try:
            subprocess.check_call(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_activity("FFmpeg not found.")
            return False

    def _check_ffmpeg_status(self) -> Dict[str, Any]:
        ok = self._check_ffmpeg()
        return {
            "status": "ok" if ok else "warning",
            "message": "FFmpeg detected" if ok else "FFmpeg not found (Optional for audio)"
        }

    def _test_wordpress(self) -> Dict[str, Any]:
        effective_env = self._load_env_values()
        if not (effective_env.get("WP_SITE_URL") and effective_env.get("WP_USERNAME") and effective_env.get("WP_APP_PASSWORD")):
            return {
                "status": "skipped",
                "message": "WP_SITE_URL / WP_USERNAME / WP_APP_PASSWORD not configured"
            }

        try:
            start = time.time()
            from utils.wordpress_client import wp_client
            posts, total_pages = wp_client.get_posts_batch(page=1, per_page=1)
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "response_time_ms": elapsed_ms,
                "message": "WordPress API accessible"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"WordPress connection failed: {e}"
            }

    def _test_woocommerce(self) -> Dict[str, Any]:
        effective_env = self._load_env_values()

        ck = effective_env.get("WOOCOMMERCE_CONSUMER_KEY")
        cs = effective_env.get("WOOCOMMERCE_CONSUMER_SECRET")
        wp_url = effective_env.get("WP_SITE_URL")

        if not ck or not cs or not wp_url:
            return {
                "status": "skipped",
                "message": "WooCommerce keys not configured"
            }

        try:
            import requests
            start = time.time()
            resp = requests.get(
                f"{wp_url}/wp-json/wc/v3/products",
                auth=(ck, cs),
                params={"per_page": 1},
                timeout=5
            )
            resp.raise_for_status()
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "response_time_ms": elapsed_ms,
                "message": "WooCommerce API accessible"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"WooCommerce connection failed: {e}"
            }

    def _test_gemini(self) -> Dict[str, Any]:
        effective_env = self._load_env_values()
        api_key = effective_env.get("GEMINI_API_KEY")

        if not api_key:
            return {"status": "skipped", "message": "GEMINI_API_KEY not configured"}

        try:
            import google.generativeai as genai
            start = time.time()
            genai.configure(api_key=api_key)
            _ = genai.list_models()
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "response_time_ms": elapsed_ms,
                "message": "Gemini API accessible"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Gemini API check failed: {e}"
            }

    def _test_lancedb(self) -> Dict[str, Any]:
        effective_env = self._load_env_values()
        db_path = effective_env.get("LANCEDB_PATH") or str(self.project_root / "data" / "lancedb")

        try:
            import lancedb
            import os
            os.makedirs(db_path, exist_ok=True)

            db = lancedb.connect(db_path)
            
            # Test write/read
            test_data = [{"id": "test", "text": "ping", "vector": [0.1] * 768}]
            if "tech_agent_test" in db.table_names():
                db.drop_table("tech_agent_test")
            table = db.create_table("tech_agent_test", data=test_data)
            _ = table.search([0.1] * 768).limit(1).to_list()
            db.drop_table("tech_agent_test")

            return {
                "status": "ok",
                "db_path": db_path,
                "writable": True,
                "message": "LanceDB accessible"
            }
        except Exception as e:
            return {
                "status": "error",
                "db_path": db_path,
                "writable": False,
                "message": f"LanceDB check failed: {e}"
            }

    def _summarize_checks(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        total = len(checks)
        passed = len([c for c in checks.values() if c.get("status") == "ok"])
        warnings = len([c for c in checks.values() if c.get("status") == "warning"])
        skipped = len([c for c in checks.values() if c.get("status") == "skipped"])
        errors = len([c for c in checks.values() if c.get("status") == "error"])

        status = "success"
        if errors:
            status = "error"
        elif warnings or skipped:
            status = "warning"

        return {
            "status": status,
            "summary": {
                "total_checks": total,
                "passed": passed,
                "warnings": warnings,
                "skipped": skipped,
                "errors": errors
            }
        }

    def _generate_recommendations(self, checks: Dict[str, Any]) -> List[str]:
        recommendations = []

        packages = checks.get("packages", {})
        missing_critical = packages.get("missing_critical", [])
        missing_optional = packages.get("missing_optional", [])
        if missing_critical or missing_optional:
            recommendations.append("安裝缺少的套件: pip install -r requirements.txt")

        env_check = checks.get("env_file", {})
        if env_check.get("status") == "error":
            recommendations.append("建立 .env 檔案（可參考 .env.example）")
        elif env_check.get("status") == "warning":
            recommendations.append("補齊建議環境變數（如 HUGGINGFACE_API_KEY）")

        directories = checks.get("directories", {})
        if directories.get("missing") or directories.get("not_writable"):
            recommendations.append("建立缺少的資料夾並確認權限（如 outputs/FUNIT 與 data/）")

        wordpress = checks.get("wordpress_connection", {})
        if wordpress.get("status") == "error":
            recommendations.append("檢查 WP_SITE_URL / WP_USERNAME / WP_APP_PASSWORD 與網路連線")

        lancedb = checks.get("lancedb", {})
        if lancedb.get("status") == "error":
            recommendations.append("檢查 LanceDB 資料夾權限與路徑設定")

        ffmpeg = checks.get("ffmpeg", {})
        if ffmpeg.get("status") == "warning":
            recommendations.append("FFmpeg 異常（選用，僅音訊轉檔需要）：請檢查或安裝（macOS: brew install ffmpeg）")

        return recommendations

    def _generate_next_steps(self, summary: Dict[str, Any]) -> List[str]:
        status = summary["status"]
        if status == "success":
            return [
                "所有檢查通過！",
                "接下來執行: /s01_品牌建構師 建立品牌指南"
            ]
        if status == "warning":
            return [
                "環境基本可用，但有警告項目可優先修正",
                "修正後可再次執行 /00_環境檢查"
            ]
        return [
            "存在錯誤，請先修正後再執行 /00_環境檢查"
        ]

# Global instance
tech_agent = TechAgent()

if __name__ == "__main__":
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description="Run TechAgent environment check")
    parser.add_argument("--full-check", action="store_true", help="Perform a full environment check")
    args = parser.parse_args()
    
    if args.full_check:
        results = tech_agent.run()
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("Please use --full-check to run the environment check.")
