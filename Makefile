.PHONY: lint test

lint:
	python -m pylint check_bareos
test:
	python -m unittest -v -b
