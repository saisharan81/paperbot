## Install project dependencies using Poetry
install:
	poetry install

## Format code with Black
fmt:
	poetry run black src/

## Lint code with Ruff
lint:
	poetry run ruff src/

## Run unit tests with pytest
test:
	poetry run pytest -q

## Run the demo entrypoint
run:
	poetry run python -m paperbot.main

## Generate candlestick charts + HTML report into ./reports/
report:
	poetry run python -m paperbot.reports.generate
