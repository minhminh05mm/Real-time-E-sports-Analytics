from pathlib import Path

from clickhouse_driver import Client
from dotenv import load_dotenv
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
SCHEMA_PATH = ROOT_DIR / "infrastructure" / "clickhouse_init" / "init_schema.sql"


def main() -> None:
    client = Client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
        user=os.getenv("CLICKHOUSE_USER", "admin"),
        password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
        database="default",
    )

    sql_text = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql_text.split(";") if statement.strip()]

    for statement in statements:
        client.execute(statement)

    print(f"Applied {len(statements)} schema statements from {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
