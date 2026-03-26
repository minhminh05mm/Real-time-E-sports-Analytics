from clickhouse_driver import Client

from stream_processing.src.config import settings


def get_clickhouse_client(database: str | None = None) -> Client:
    return Client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=database or settings.clickhouse_database,
    )


def insert_rows(client: Client, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    client.execute(f"INSERT INTO {table_name} VALUES", rows)
