.PHONY: test quality style

check_dirs := platogram tests

test:
	pytest --cov=platogram -n auto tests

quality:
	ruff check $(check_dirs)

style:
	ruff format $(check_dirs)

typecheck:
	mypy $(check_dirs)
