"""兼容原有脚本用法，结果仍保存到本项目的 results 文件夹。"""

from pathlib import Path

from dotenv import load_dotenv
from tomarkdown.cli import main

if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    load_dotenv(project_dir / ".env")
    raise SystemExit(main(results_dir=project_dir / "results"))
