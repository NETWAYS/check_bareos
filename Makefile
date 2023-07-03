.PHONY: lint test

lint:
	python -m pylint check_bareos

test:
	python -m unittest -v test_check_bareos.py
coverage:
	python -m coverage run -m unittest test_check_bareos.py
	python -m coverage report -m --include check_bareos.py
