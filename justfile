test_quick:
    poetry run coverage run -m pytest
    @poetry run coverage report

doc:
    tox -e doc

test:
    tox
