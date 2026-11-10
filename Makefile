PYTHON ?= python3
RUFF ?= uvx ruff
DIST_DIR := dist

.PHONY: lint format test export clean

lint:
	$(RUFF) format --check .
	$(RUFF) check .
	$(PYTHON) tools/validate.py
	$(PYTHON) tools/vendor.py --check
	$(PYTHON) tools/hygiene.py files

format:
	$(RUFF) check --fix .
	$(RUFF) format .
	$(PYTHON) tools/vendor.py --write

test:
	$(PYTHON) -m unittest discover -s tests -t .

export: lint test clean
	$(PYTHON) tools/package.py --zip --out "$(DIST_DIR)"

clean:
	$(RM) -r "$(DIST_DIR)"
