.PHONY: clean_notebooks bump dist release create-release install upload docs

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(wildcard *.egg-info)
CURRENT_VERSION := $(shell jq -r .version js/package.json)

JQ_RULES := '(.cells[] | select(has("outputs")) | .outputs) = [] \
| (.cells[] | select(has("execution_count")) | .execution_count) = null \
| .metadata = { \
	"language_info": {"name":"python", "pygments_lexer": "ipython3"}, \
	"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"} \
} \
| .cells[].metadata = {}'

clean_notebooks: ./notebooks/*
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
	@echo Current version: $(CURRENT_VERSION)
ifdef part
	bump-my-version bump $(part) --allow-dirty && grep current pyproject.toml
else ifdef version
	bump-my-version bump --allow-dirty --new-version $(version) && grep current pyproject.toml
else
	@echo "Provide part=major|minor|patch|release|build and optionally version=x.y.z..."
	exit 1
endif

# Dist commands

dist:
	@rm -f dist/*
	@rm -f js/dist/*
	@rm -fr cad_viewer_widget/labextension/*
	hatch build

docs:
	@pdoc3 --force --config show_source_code=False --html --output-dir docs cad_viewer_widget

release:
	git add .
	git status
	git diff-index --quiet HEAD || git commit -m "Latest release: $(CURRENT_VERSION)"
	git tag -a v$(CURRENT_VERSION) -m "Latest release: $(CURRENT_VERSION)"

create-release:
	@github-release release -u bernhard-42 -r cad-viewer-widget -t v$(CURRENT_VERSION) -n cad-viewer-widget-$(CURRENT_VERSION)
	@sleep 2
	@github-release upload  -u bernhard-42 -r cad-viewer-widget -t v$(CURRENT_VERSION) -n cad_viewer_widget-$(CURRENT_VERSION).tar.gz -f dist/cad_viewer_widget-$(CURRENT_VERSION).tar.gz
	@github-release upload  -u bernhard-42 -r cad-viewer-widget -t v$(CURRENT_VERSION) -n cad_viewer_widget-$(CURRENT_VERSION)-py3-none-any.whl -f dist/cad_viewer_widget-$(CURRENT_VERSION)-py3-none-any.whl

install: dist
	@echo "=> Installing cad-viewer-widget"
	@pip install --upgrade .

check_dist:
	@twine check dist/*

upload:
	@twine upload dist/*

upload_js:
	@cd js && npm publish
	