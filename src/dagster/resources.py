import dagster as dg
import duckdb


class MotherDuckS3Resource(dg.ConfigurableResource):
    motherduck_token: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str

    def get_connection(self, database: str) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            f"md:{database}?motherduck_token={self.motherduck_token}"
        )

    def _create_s3_secret(
        self,
        conn: duckdb.DuckDBPyConnection,
        scope: str | None = None
    ) -> None:
        """
        Create or replace a secret in MotherDuck for accessing S3.
        Parameters:
            conn: The DuckDB connection to use for executing the SQL command.
            scope: Optional scope for the secret. If provided, the secret will be created within the given bucket scope.
            If not provided, the secret will be created at the global level for all buckets. 's3://my-bucket'
        """
        scope_sql = f", SCOPE '{scope}'" if scope else ""
        conn.execute(f"""
            CREATE OR REPLACE SECRET aws_s3_secret (
                TYPE S3,
                KEY_ID '{self.aws_access_key_id}',
                SECRET '{self.aws_secret_access_key}',
                REGION '{self.aws_region}'
                {scope_sql}
            )
        """)

    def _table_exists(
        self,
        conn: duckdb.DuckDBPyConnection,
        schema: str,
        table_name: str
    ) -> bool:
        result = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_name = '{table_name}'
            """
        ).fetchone()
        return result[0] > 0

    def copy_into_duckdb(
        self,
        s3_path: str,
        database: str,
        table_name: str,
        schema: str,
        file_format: str = "parquet",
        mode: str | None = None,
        hive_partitioning: bool = False,
        scope: str | None = None,
    ) -> None:
        """
        Load data from S3 into a MotherDuck table.
        Parameters:
            s3_path: The S3 path to the data (e.g., 's3://my-bucket/path/to/data').
            database: The name of the MotherDuck database.
            table_name: The name of the MotherDuck table to create or append to.
            schema: The schema of the MotherDuck table.
            file_format: The format of the data in S3 ('parquet', 'csv', or 'json').
            mode: The mode for loading data ('create_or_replace' or 'append'). If not provided, it will default to 'append' if the table exists, or 'create_or_replace' if it does not.
            hive_partitioning: Whether to enable Hive partitioning when reading Parquet files. Only applicable if file_format is 'parquet'.
            scope: Optional scope for the S3 secret. If provided, the secret will be created within the given bucket scope. If not provided, the secret will be created at the global level for all buckets.
        """
        # Get connection and create S3 secret if needed
        conn = self.get_connection(database=database)
        self._create_s3_secret(conn, scope=scope)

        # Check for schema
        if not conn.execute(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema}'").fetchone():
            conn.execute(f"CREATE SCHEMA {schema}")

        # Resolve SQL for reading from S3 based on file format and mode
        readers = {
            "parquet": f"read_parquet('{s3_path}/**/*.parquet', hive_partitioning={str(hive_partitioning).lower()})",
            "csv": f"read_csv('{s3_path}/**/*.csv', header=true, auto_detect=true)",
            "json": f"read_json_auto('{s3_path}/**/*.json')",
        }
        source_sql = readers[file_format.lower()]
        effective_mode = mode or ("append" if self._table_exists(conn, schema, table_name) else "create_or_replace")
        sql_by_mode = {
            "create_or_replace": f"CREATE OR REPLACE TABLE {schema}.{table_name} AS SELECT * FROM {source_sql}",
            "append": f"INSERT INTO {schema}.{table_name} SELECT * FROM {source_sql}",
        }
        try:
            sql = sql_by_mode[effective_mode]
        except KeyError:
            raise ValueError("mode must be 'create_or_replace' or 'append'")

        conn.execute(sql)
        conn.close()
