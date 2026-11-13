import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]

class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction"""
        clean = df[MOVIE_COLUMNS].astype(object).where(pd.notna(df[MOVIE_COLUMNS]), None)
        rows = list(clean.itertuples(index=False, name=None))

        connection = get_connection(self.db_path)
        try:
            connection.execute("DELETE FROM movies")
            connection.executemany(
                "INSERT INTO movies (title, release_year, rating, genre) VALUES (?, ?, ?, ?)",
                rows
            )
            connection.commit()
            logger.debug(f"Stored movies in SQLite: rows={len(rows)}")
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = """
                SELECT title, release_year, rating, genre
                FROM movies
                ORDER BY id
                """
            rows = connection.execute(sql_statement).fetchall()
            logger.debug(f"Retrieved movies from SQLite: rows={len(rows)}")
            return pd.DataFrame([dict(row) for row in rows], columns=MOVIE_COLUMNS)
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"""
            SELECT {selected_columns}
            FROM movies
            ORDER BY id
            LIMIT ?
            """
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            logger.debug(f"Select columns: {columns}, rows={len(rows)}")
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT COUNT(*) AS total FROM movies"
            row = connection.execute(sql_statement).fetchone()
            logger.debug(f"Counted movies: total={row['total']}")
            return row["total"]
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        # TODO: validate columns as in select_columns().
        # SELECT id plus those columns and filter by minimum rating.
        # Sort by rating DESC then id ASC, and apply limit.
        # Return dictionaries and log the selected columns and row count at DEBUG.
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least on column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"""
                SELECT {selected_columns}
                FROM movies
                WHERE rating >= ?
                ORDER BY rating DESC, id ASC
                LIMIT ?
                """
            rows = connection.execute(sql_statement, (min_rating, limit)).fetchall()
            logger.debug(f"Queried movies: columns={columns}, rows={len(rows)}")
            return [dict(row) for row in rows]
        finally:
             connection.close()



class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0


    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        self._counter += 1
        dataset_id = self._counter

        self._store[dataset_id] = {"filename": filename, "data": df.copy()}

        logger.debug(f"Stored dataset: id={dataset_id}, rows={len(df)}")

        return dataset_id


    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        item = self._store.get(dataset_id)
        if item is None:
            logger.debug(f"Dataset not found: id={dataset_id}")
            return None

        logger.debug(f"Retrieved dataset copy: id={dataset_id}, rows={len(item['data'])}")

        return item["data"].copy()


    def get_metadata(self, dataset_id):
        """Return the dataset metadata, or None."""
        item = self._store.get(dataset_id)
        if item is None:
            logger.debug(f"Metadata not found: id={dataset_id}")
            return None

        logger.debug(f"Retrieved metadata: id={dataset_id}")

        return {
            "id": dataset_id,
            "filename": item["filename"],
            "rows": item["data"].shape[0],
            "columns": item["data"].shape[1],
            "column_names": item["data"].columns.tolist()
        }


    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if
        missing."""
        item = self._store.get(dataset_id)
        if item is None:
            logger.debug(f"Cannot update missing dataset: id={dataset_id}")
            return False

        item["data"] = df.copy()
        logger.debug(f"Updated dataset: id={dataset_id}, rows={len(df)}")
        return True


    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
        logger.debug("Cleared all data and reset ID counter")