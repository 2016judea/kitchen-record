PY=.venv/bin/python
all: fetch build
fetch:
	$(PY) scripts/fetch.py
build:
	$(PY) scripts/build.py
	$(PY) scripts/build_for.py
test:
	$(PY) -m pytest -q tests 2>&1 | tee data/pytest.log
	node --test tests/*.test.js 2>&1 | tee data/node.log
deploy:
	$(PY) scripts/deploy.py
