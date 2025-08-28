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
	@./$(PIP) install src/cosim_toolbox/.

# venv is a shortcut target
venv: $(VENV)/bin/activate

run: venv
	.$(PYTHON) app.py

clean:
	@echo "Deleting venv, *.pyc, and test coverage data..."
	@rm -rf $(VENV)
	@rm -rf .coverage coverage.xml results.xml .pytest_cache htmlcov docs/_build
	@find . -type f -name '*.pyc' -delete

docs:
	@echo "Creating HTML "read the docs" website"
	@. $(VENV)/bin/activate; cd ./docs; make html

test:
	@echo "Running tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=20 --junitxml results.xml -v src/cosim_toolbox/tests

integration-test:
	@echo "Running integration tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=2 --junitxml results.xml -v \
		src/cosim_toolbox/integration_tests/test_simple_federation.py \
		src/cosim_toolbox/integration_tests/test_readerDB.py \
		src/cosim_toolbox/integration_tests/test_dbConfigs.py

.PHONY: all venv run clean docs test coverage integration-test