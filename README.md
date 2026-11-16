# MP3: Movie Data API with SQLite and Caching

This project is a FastAPI application that stores a movie collection in a SQLite database, lets clients filter it with SQL, cleans it using the MP1 data pipeline, and caches repeated retrievals. Clients upload a CSV with `POST /upload`, which checks the columns and replaces the stored collection in a single SQL transaction, so the data persists after the server restarts. `GET /movies` returns the stored movies and their total count, and `GET /movies/search` filters by minimum rating and returns only the selected columns, using SQL to filter, sort, and limit the results. `POST /movies/process` loads the collection, validates and cleans it with the reused `data_pipeline` modules, and saves the result back to SQLite. In `src/`, `database.py` creates the connection and table, `storage.py` runs the SQL queries, `cache.py` stores recent `GET /movies` responses in FakeRedis for 90 seconds, and `models.py` defines the request and response formats. After every successful upload or processing step, the cache is cleared, so later requests never return outdated data. Middleware logs every request with a unique request ID, status code, and duration.

## Running the API

```bash
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs to try the endpoints.

## Running the Tests

```bash
python -m pytest tests -v
```

## Sample Processing Request

After uploading `fixtures/sample_movies.csv`, use these settings in `POST /movies/process`:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {"enabled": true, "columns": ["rating"], "method": "iqr", "threshold": 1.5}
  }
}
```

Expected result:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```