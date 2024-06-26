#!/usr/bin/make -f

TOPDIR := $(realpath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
SELF := $(abspath $(lastword $(MAKEFILE_LIST)))

GITHUB_RUN_ID ?= 0

DATE := $(shell date +"%Y%m%d")
VERSION := $(shell git describe --tags --always --match='v[0-9]*' | cut -d '-' -f 1 | tr -d 'v')
RELEASE := $(shell git describe --tags --always --match='v[0-9]*' --long | cut -d '-' -f 2)
BUILD := $(shell git describe --tags --long --always --dirty)-$(DATE)-$(GITHUB_RUN_ID)

define __VERSION_CONTENT__
"""
Dynamic version info

Generated by $(SELF)
  on $(shell hostname)
  at $(shell date +"%Y-%m-%d %H:%M:%S %Z")
"""

__version__ = '$(VERSION)'
__release__ = '$(RELEASE)'
__build__ = '$(BUILD)'
endef
export __VERSION_CONTENT__

SHOW_ENV_VARS = \
	VERSION \
	RELEASE \
	GITHUB_RUN_ID \
	BUILD

help: ## Show help message (list targets)
	@awk 'BEGIN {FS = ":.*##"; printf "\nTargets:\n"} /^[$$()% 0-9a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(SELF)

show-var-%:
	@{ \
	escaped_v="$(subst ",\",$($*))" ; \
	if [ -n "$$escaped_v" ]; then v="$$escaped_v"; else v="(undefined)"; fi; \
	printf "%-13s %s\n" "$*" "$$v"; \
	}

show-env: $(addprefix show-var-, $(SHOW_ENV_VARS)) ## Show environment details

.PHONY: src/zont_api/version.py
src/zont_api/version.py:
	@printf "%s\n" "$${__VERSION_CONTENT__}" >$@

.PHONY: version
version: src/zont_api/version.py
	@printf "%s\n" "$(VERSION)" >VERSION

build: version ## Build a module with python -m build
	tox run -e build

test: version ## Run tests
	tox run

lint: version ## Run linters
	tox run -e lint

fmt: version ## Run formatters
	tox run -e fmt

venv: version ## Create virtualenv
	tox devenv --list-dependencies .venv

clean: ## Clean up
	find $(TOPDIR)/ -type f -name "*.pyc" -delete
	find $(TOPDIR)/ -type f -name "*.pyo" -delete
	find $(TOPDIR)/ -type d -name "__pycache__" -delete
	for dir in .pytest_cache .tox build dist htmlcov src/zont_api.egg-info; do \
		rm -rf $(TOPDIR)/$${dir} ; \
	done
	rm -f $(TOPDIR)/.coverage
	rm -rf $(TOPDIR)/htmlcov-py*
	rm -f $(TOPDIR)/src/zont_api/version.py $(TOPDIR)/VERSION

.PHONY: build test lint fmt venv clean
