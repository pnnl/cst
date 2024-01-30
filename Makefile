# define the name of the virtual environment directory
VENV := venv
PYTHON := $(VENV)/bin/python3.10
PIP := $(VENV)/bin/pip


# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate: src/cosim_toolbox/requirements.txt
	@echo "Creating Python virtual environment at ./venv/..."
	@python3 -m venv $(VENV)
	@echo "Installing requirements..."
	@./$(PIP) install -r src/cosim_toolbox/requirements.txt

# venv is a shortcut target
venv: $(VENV)/bin/activate

run: venv
	.$(PYTHON) app.py

clean:
	@echo "Deleting venv, *.pyc, and test coverage data..."
	@rm -rf $(VENV)
	@rm -rf .coverage coverage.xml results.xml .pytest_cache htmlcov
	@find . -type f -name '*.pyc' -delete

test:
	@echo "Running tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=2 --junitxml results.xml -v src/cosim_toolbox/tests/test_helics_config.py

.PHONY: all venv run clean test coverage