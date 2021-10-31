.PHONY: clean_notebooks bump dist release install upload

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(wildcard *.egg-info)
CURRENT_VERSION := $(shell awk '/current_version/ {print $$3}' setup.cfg)

JQ_RULES := '(.cells[] | select(has("outputs")) | .outputs) = [] \
| (.cells[] | select(has("execution_count")) | .execution_count) = null \
| .metadata = { \
	"language_info": {"name":"python", "pygments_lexer": "ipython3"}, \
	"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"} \
} \
| .cells[].metadata = {}'

clean_notebooks: ./test.ipynb
	@for file in $^ ; do \
		echo "$${file}" ; \
		jq --indent 1 $(JQ_RULES) "$${file}" > "$${file}_clean"; \
		mv "$${file}_clean" "$${file}"; \
		python validate_nb.py "$${file}"; \
	done

clean: clean_notebooks
	@echo "=> Cleaning"
	@rm -fr build dist $(EGGS) $(PYCACHE)
	@rm -f js/dist/*

prepare: clean
	git add .
	git status
	git commit -m "cleanup before release"

bump:
ifdef part
ifdef version
	bumpversion --new-version $(version) $(part) && grep current setup.cfg
else
	bumpversion --allow-dirty $(part) && grep current setup.cfg
endif
else
	@echo "Provide part=major|minor|patch|release|build and optionally version=x.y.z..."
	exit 1
endif

# Dist commands

dist:
	@rm -f dist/*
	@rm -f js/dist/*
	python setup.py sdist bdist_wheel

release:
	git add .
	git status
	git diff-index --quiet HEAD || git commit -m "Latest release: $(CURRENT_VERSION)"
	git tag -a v$(CURRENT_VERSION) -m "Latest release: $(CURRENT_VERSION)"

install: dist
	@echo "=> Installing cad-viewer-widget"
	@pip install --upgrade .

check_dist:
	@twine check dist/*

upload:
	@twine upload dist/*

upload_js:
	@cd js && npm publish
	