from contextlib import contextmanager

import dagster as dg
import duckdb

from .sql import render_sql

_SUPPORTED_FORMATS = ("parquet", "csv", "json")


class MotherDuckS3Resource(dg.ConfigurableResource):
    motherduck_token: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    metadata_schema: str = "_s3_meta"

    @contextmanager
    def motherduck_connection(self, database: str):
        conn = duckdb.connect(f"md:{database}?motherduck_token={self.motherduck_token}")
        try:
            yield conn
        finally:
            conn.close()

    def _check_file_format(self, file_format: str) -> None:
        file_format = file_format.lower()
        if file_format not in _SUPPORTED_FORMATS:
            raise ValueError(f"file_format must be one of {_SUPPORTED_FORMATS}")

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
        conn.execute(
            render_sql(
                "create_secret.sql.j2",
                key_id=self.aws_access_key_id,
                secret=self.aws_secret_access_key,
                region=self.aws_region,
                scope=scope,
            )
        )

    def _create_schema_if_not_exists(
        self,
        conn: duckdb.DuckDBPyConnection,
        schema: str
    ) -> None:
        conn.execute(render_sql("create_schema.sql.j2", schema=schema))

    def _metadata_table_naming(self, schema: str, table_name: str) -> str:
        return f"{schema}__{table_name}__loaded_files"

    def _track_metadata(
        self,
        conn: duckdb.DuckDBPyConnection,
        schema: str,
        table_name: str
    ) -> None:
        """
        Create a metadata table to track loaded files in MotherDuck.
        Parameters:
            conn: The DuckDB connection to use for executing the SQL command.
            schema: The schema where the target table resides.
            table_name: The name of the target table for which to track loaded files.
        """
        conn.execute(render_sql("create_schema.sql.j2", schema=self.metadata_schema))
        conn.execute(
            render_sql(
                "create_metadata_table.sql.j2",
                meta_schema=self.metadata_schema,
                meta_table=self._metadata_table_naming(schema, table_name),
            )
        )

    def list_files_to_load(
        self,
        conn: duckdb.DuckDBPyConnection,
        s3_path: str,
        schema: str,
        table_name: str,
        file_format: str = "parquet",
        full_refresh: bool = False
    ) -> list[str]:
        pattern = f"{s3_path.rstrip('/')}/**/*.{file_format}"
        source_files = [
            row[0]
            for row in conn.execute(
                render_sql("list_source_files.sql.j2", pattern=pattern)
            ).fetchall()
        ]

        if full_refresh:
            files_to_load = source_files
        else:
            loaded = {
                row[0]
                for row in conn.execute(
                    render_sql(
                        "list_loaded_files.sql.j2",
                        meta_schema=self.metadata_schema,
                        meta_table=self._metadata_table_naming(schema, table_name),
                        target_schema=schema,
                        target_table=table_name,
                    )
                ).fetchall()
            }
            files_to_load = [f for f in source_files if f not in loaded]

        if not files_to_load:
            return []

        return files_to_load

    def copy_into_duckdb(
        self,
        s3_path: str,
        database: str,
        table_name: str,
        schema: str,
        file_format: str = "parquet",
        scope: str | None = None,
        full_refresh: bool = False,
    ) -> None:
        """
        Load data from S3 into a MotherDuck table.
        Parameters:
            s3_path: The S3 path to the data (e.g., 's3://my-bucket/path/to/data').
            database: The name of the MotherDuck database.
            table_name: The name of the MotherDuck table to create or append to.
            schema: The schema of the MotherDuck table.
            file_format: The format of the data in S3 ('parquet', 'csv', or 'json').
            full_refresh: Whether to perform a full refresh of the table. If True, the table will be recreated; if False, new data will be appended.
            scope: Optional scope for the S3 secret. If provided, the secret will be created within the given bucket scope. If not provided, the secret will be created at the global level for all buckets.
        """
        self._check_file_format(file_format)
        # Get connection and create S3 secret if needed
        with self.motherduck_connection(database=database) as conn:
            self._create_s3_secret(conn=conn, scope=scope)
            self._create_schema_if_not_exists(conn=conn, schema=schema)
            self._track_metadata(conn=conn, schema=schema, table_name=table_name)
            files_to_load = self.list_files_to_load(
                conn=conn,
                s3_path=s3_path,
                schema=schema,
                table_name=table_name,
                file_format=file_format
            )
            if not files_to_load:
                
                return

            conn.execute(
                render_sql(
                    "create_table.sql.j2",
                    schema=schema,
                    table=table_name,
                    file_format=file_format,
                    files=files_to_load,
                    full_refresh=full_refresh,
                )
            )
            if not full_refresh:
                conn.execute(
                    render_sql(
                        "insert_files.sql.j2",
                        schema=schema,
                        table=table_name,
                        file_format=file_format,
                        files=files_to_load,
                    )
                )

            if full_refresh:
                conn.execute(
                    render_sql(
                        "delete_loaded_files.sql.j2",
                        meta_schema=self.metadata_schema,
                        meta_table=self._metadata_table_naming(schema, table_name),
                        target_schema=schema,
                        target_table=table_name,
                    )
                )
            conn.execute(
                render_sql(
                    "record_loaded_files.sql.j2",
                    meta_schema=self.metadata_schema,
                    meta_table=self._metadata_table_naming(schema, table_name),
                    target_schema=schema,
                    target_table=table_name,
                    files=files_to_load,
                )
            )
