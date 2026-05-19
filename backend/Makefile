# GridCheck backend — lokale Hilfsziele (PowerShell: make via Git Bash oder WSL)

PYTHON ?= .venv/Scripts/python.exe

.PHONY: data-pipeline ki-export-dataset test-data-pipeline

data-pipeline:
	$(PYTHON) scripts/run_data_source_pipeline.py

ki-export-dataset:
	$(PYTHON) scripts/export_ki_feedback_dataset.py

test-data-pipeline:
	pytest tests/test_data_source_pipeline.py -q
