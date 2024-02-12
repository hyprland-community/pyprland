test_quick:
    poetry run coverage run -m pytest
    @poetry run coverage report

doc:
    tox -e doc

wiki:
    tox -e wiki

test:
    tox

