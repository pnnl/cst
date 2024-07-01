# define the name of the virtual environment directory
VENV := venv
PYTHON := $(VENV)/bin/python3.10
PIP := $(VENV)/bin/pip

JULIA := julia
JULIA_PROJECT_PATH := src/cosim_toolbox
JULIA_TEST_SCRIPT := src/cosim_toolbox/tests/test_my_module.jl

# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate: src/cosim_toolbox/requirements.txt
	@echo "Creating Python virtual environment at ./venv/..."
	@python3 -m venv $(VENV)
	@echo "Installing requirements..."
	@./$(PIP) install -r src/cosim_toolbox/requirements.txt

# venv is a shortcut target
venv: $(VENV)/bin/activate

# Target to create a Julia project environment and install dependencies
venv-julia:
	@echo "Creating Julia project environment and installing dependencies..."
	@$(JULIA) --project=$(JULIA_PROJECT_PATH) -e 'using Pkg; Pkg.activate("."); Pkg.add("Test"); Pkg.add("Coverage");'

run: venv
	.$(PYTHON) app.py

clean:
	@echo "Deleting venv, *.pyc, and test coverage data..."
	@rm -rf $(VENV)
	@rm -rf .coverage coverage.xml results.xml .pytest_cache htmlcov
	@find . -type f -name '*.pyc' -delete

test-julia:
	$(JULIA) --project=src/cosim_toolbox $(JULIA_TEST_SCRIPT)

test:
	@echo "Running tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=20 --junitxml results.xml -v src/cosim_toolbox/tests

integration-test:
	@echo "Running integration tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=cosim_toolbox --cov-fail-under=2 --junitxml results.xml -v \
		src/cosim_toolbox/integration-tests/test_simple_federation.py

.PHONY: all venv run clean test test-julia coverage integration-test