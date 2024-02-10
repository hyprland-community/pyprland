test:
    tox

doc:
    tox -e doc

test_all: test_cover test_lint test_wiki

test_wiki:
    @./scripts/test_wiki_coverage.sh

test_cover:
    poetry run coverage run -m pytest
    @poetry run coverage report

test_lint:
    poetry run mypy pyprland
    poetry run vulture --ignore-names 'event_*,run_*,from*,instance' pyprland v_whitelist.py
