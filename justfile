test_quick:
    .tox/py311/bin/coverage run -m pytest
    .tox/py311/bin/coverage report

doc:
    tox -e doc

wiki:
    tox -e wiki

test:
    tox

release:
    ./scripts/make_release
