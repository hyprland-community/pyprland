test_quick:
    .tox/py311/bin/coverage run -m pytest
    .tox/py311/bin/coverage report

doc:
    tox run -e doc

wiki:
    tox run -e wiki

test:
    tox run

release:
    ./scripts/make_release
