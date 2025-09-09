# define the name of the virtual environment directory
VENV := venv
PYTHON := $(VENV)/bin/python3.12
PIP := $(VENV)/bin/pip

# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate:
	@echo "Creating Python virtual environment at ./venv/..."
	@python3.12 -m venv $(VENV)
	@echo "Installing requirements..."
	@./$(PIP) install -r requirements.txt
	@./$(PIP) install src/.

# venv is a shortcut target
venv: $(VENV)/bin/activate

run: venv
	.$(PYTHON) app.py

clean:
	@echo "Deleting venv, *.pyc, and test coverage data..."
	@rm -rf $(VENV)
	@rm -rf .coverage coverage.xml results.xml .pytest_cache htmlcov
	@rm -rf  docs/_build src/build src/cosim_toolbox.egg-info
	@find . -type f -name '*.pyc' -delete

docs:
	@echo "Creating HTML "read the docs" website"
	@. $(VENV)/bin/activate; cd ./docs; make html

tests:
	@echo "Running tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=20 --junitxml results.xml -v src/tests

integration_tests:
	@echo "Running integration tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=2 --junitxml results.xml -v \
		src/integration_tests/test_simple_federation.py \
		src/integration_tests/test_readerDB.py \
		src/integration_tests/test_dbConfigs.py

.PHONY: all venv run clean docs tests coverage integration_tests