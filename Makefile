.PHONY: clean_notebooks bump check dist release create-release install upload docs

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

# The traitlets cannot be generated - ipywidgets needs each one declared with
# its type - so they are checked instead, against ocp-viewer-core's vocabulary.
# Needs the environment the widget is installed in, for ocp_viewer_core.
check:
	@python check_traits.py

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

# Push, then a GitHub release under the tag `release` made, carrying what
# PyPI got. No `--target`: the tag exists and says which commit, whichever
# branch the release was cut from. Both files must exist in dist/ - `make
# dist` builds them - or nothing is pushed.
create-release:
	@for f in dist/cad_viewer_widget-$(CURRENT_VERSION)-py3-none-any.whl \
	         dist/cad_viewer_widget-$(CURRENT_VERSION).tar.gz; do \
	    test -f $$f || { echo "missing $$f - run make dist first"; exit 1; }; \
	done
	@git push
	@git push --tags
	@gh release create v$(CURRENT_VERSION) \
	    "dist/cad_viewer_widget-$(CURRENT_VERSION)-py3-none-any.whl#Python $(CURRENT_VERSION) - wheel (PyPI)" \
	    "dist/cad_viewer_widget-$(CURRENT_VERSION).tar.gz#Python $(CURRENT_VERSION) - source (PyPI)" \
	    --title "cad-viewer-widget $(CURRENT_VERSION)" \
	    --notes "$(CURRENT_VERSION) on PyPI and npm. See the commit log."

install: dist
	@echo "=> Installing cad-viewer-widget"
	@pip install --upgrade .

check_dist:
	@twine check dist/*

upload:
	@twine upload dist/*

upload_js:
	@cd js && npm publish
	