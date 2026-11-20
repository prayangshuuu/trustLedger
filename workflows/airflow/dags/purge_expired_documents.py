"""Airflow DAG: purge_expired_documents (schedule 30 0 * * *). Logic lives in workflows/airflow/tasks.py."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from workflows.airflow import tasks

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:  # Airflow is optional; tasks stay importable for tests
    DAG = None

if DAG is not None:
    with DAG(
        dag_id="purge_expired_documents",
        schedule="30 0 * * *",
        start_date=datetime(2026, 11, 1),
        catchup=False,
        tags=["trustledger"],
    ) as dag:
        PythonOperator(
            task_id="purge_expired_documents", python_callable=tasks.purge_expired_documents
        )
