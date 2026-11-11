# Specwright — single entry point for quality, tests, builds and distribution.
# Targets hold orchestration only; every real command lives in a Python tool or
# the shared test runner.
#
# Usage: make <group> [command…] [VAR=value]
#   make test               runs the group's default (unit tests)
#   make lint validate      runs commands of one group, in order
#   make package            clean, build and package every public skill
#   make                    draws every group and command as a tree
#
# Conventions for `make help`:
#   ##@ group: text          declares a group (→ marks what the bare group runs)
#   ## group.command: text   documents a command inside that group
# Plain comments are ignored, so they can explain a target without listing it.

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3
RUFF ?= uvx ruff
DIST_DIR := dist

GROUPS := lint format test build package clean
RUNNABLE := lint format test build package clean

# Group colour, as "group=SGR" pairs; help adds the bold attribute.
GROUP_COLORS := lint=33 format=32 test=35 build=34 package=96 clean=37

# ---------------------------------------------------------------------------
# Subcommand dispatch: `make lint validate` runs lint.validate. The words after
# the group become no-op goals so make does not try to build them.
# ---------------------------------------------------------------------------

ifneq ($(filter $(firstword $(MAKECMDGOALS)),$(GROUPS)),)
COMMANDS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
ifneq ($(COMMANDS),)
.PHONY: $(COMMANDS)
$(COMMANDS):
	@:
endif
endif

$(GROUPS):
	@for command in $(COMMANDS); do \
		grep -qE "^## $@\.$$command: " $(firstword $(MAKEFILE_LIST)) || { \
			echo "unknown command: make $@ $$command"; \
			$(MAKE) --no-print-directory help GROUP=$@; \
			exit 2; \
		}; \
	done
	@$(MAKE) --no-print-directory $(if $(COMMANDS),$(addprefix $@.,$(COMMANDS)),$(if $(filter $@,$(RUNNABLE)),$@.default,help GROUP=$@))

##@ lint: → format check, Ruff, source validation, vendor, bundle-map and hygiene checks

lint.default: lint.format lint.ruff lint.validate lint.vendor lint.bundle lint.hygiene

## lint.format: check formatting without writing
lint.format:
	$(RUFF) format --check .

## lint.ruff: lint Python sources
lint.ruff:
	$(RUFF) check .

## lint.validate: validate skill sources and repository contracts
lint.validate:
	$(PYTHON) tools/validate.py

## lint.vendor: fail when a skill vendors a duplicate of skills/_shared
lint.vendor:
	$(PYTHON) tools/vendor.py --check

## lint.bundle: fail when bundle-map.json drifts from real imports, links or the file cap
lint.bundle:
	$(PYTHON) tools/bundle.py --check

## lint.hygiene: scan text for work-tracking labels and attribution
lint.hygiene:
	$(PYTHON) tools/hygiene.py files

##@ format: → apply Ruff fixes, format sources, regenerate vendored files and the bundle map

format.default: format.ruff format.write format.vendor format.bundle

## format.ruff: apply Ruff's safe lint fixes
format.ruff:
	$(RUFF) check --fix .

## format.write: format Python sources
format.write:
	$(RUFF) format .

## format.vendor: regenerate vendored shared code
format.vendor:
	$(PYTHON) tools/vendor.py --write

## format.bundle: regenerate each skill's shared-file list in bundle-map.json
format.bundle:
	$(PYTHON) tools/bundle.py --write

##@ test: → the unit test suite

test.default: test.unit

## test.unit: run the unit test suite
test.unit:
	$(PYTHON) -m unittest discover -s tests -t .

## test.docker: run the unit test suite in Python 3.13 with git installed
test.docker:
	docker run --rm -v "$(CURDIR):/workspace:ro" -w /workspace python:3.13-slim \
		sh -ec 'apt-get update -qq && \
		        apt-get install -y -qq --no-install-recommends git && \
		        PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -t .'

##@ build: → lint and test the repository

build.default: lint.default test.default
	@echo "build: lint and tests passed"

##@ package: → clean, build and write one self-contained ZIP per public skill

package.default: clean.default build.default package.zip

## package.zip: package every public skill into dist/
package.zip:
	$(PYTHON) tools/package.py --zip --out "$(DIST_DIR)"

## package.report: show each skill's file count, size and shared capabilities
package.report:
	$(PYTHON) tools/bundle.py --report

##@ clean: → remove distribution output, caches and Python bytecode

clean.default:
	rm -rf "$(DIST_DIR)" build .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# ---------------------------------------------------------------------------
# Help: draws the groups and their commands as a tree. GROUP=<name> narrows it;
# NO_COLOR=1 or FORCE_COLOR=0/1 overrides the terminal detection.
# ---------------------------------------------------------------------------

help:
	@if [ -t 1 ]; then tty=yes; else tty=; fi; \
	awk -v colors='$(GROUP_COLORS)' -v only='$(GROUP)' -v tty="$$tty" \
		-v force='$(if $(FORCE_COLOR),$(if $(filter-out 0 no false,$(FORCE_COLOR)),yes,no))' ' \
	function paint(code, text) { \
		return plain ? text : code text reset \
	} \
	function rule(   line, i) { \
		for (i = 0; i < 9 + width + 56; i++) line = line "─"; \
		return "  " paint(dim, line) \
	} \
	function hint(text) { \
		if (!match(text, /\([^)]*=[^)]*\)/)) return text; \
		return substr(text, 1, RSTART - 1) paint(yellow, substr(text, RSTART, RLENGTH)) substr(text, RSTART + RLENGTH) \
	} \
	function usage(left, right) { \
		printf "  %s  %s\n", paint(bold, sprintf("%-" (width + 7) "s", left)), paint(dim, right) \
	} \
	BEGIN { \
		reset = "\033[0m"; dim = "\033[2m"; bold = "\033[1m"; yellow = "\033[33m"; \
		plain = (ENVIRON["NO_COLOR"] != "" || force == "no" || (tty == "" && force != "yes")); \
		split(colors, spec, " "); \
		for (i in spec) { split(spec[i], kv, "="); col[kv[1]] = "\033[" kv[2] ";1m" } \
	} \
	/^##@ [a-z]+: / { \
		entry = substr($$0, 5); cut = index(entry, ": "); \
		groups++; gname[groups] = substr(entry, 1, cut - 1); gabout[groups] = substr(entry, cut + 2); \
		next \
	} \
	/^## [a-z]+\.[a-z0-9-]+: / { \
		entry = substr($$0, 4); cut = index(entry, ": "); full = substr(entry, 1, cut - 1); \
		dot = index(full, "."); \
		total++; owner[total] = substr(full, 1, dot - 1); \
		name[total] = substr(full, dot + 1); about[total] = substr(entry, cut + 2); \
		if (length(name[total]) > width) width = length(name[total]) \
	} \
	END { \
		printf "\n  %s %s\n", paint(bold, "Specwright"), \
			paint(dim, only == "" ? "· make <group> [command…] [VAR=value]" : "· make " only " <command…> [VAR=value]"); \
		print rule(); \
		for (g = 1; g <= groups; g++) { \
			group = gname[g]; \
			if (only != "" && only != group) continue; \
			about_group = gabout[g]; \
			if (sub(/^→ /, "", about_group)) \
				about_group = paint(col[group], "→") " " about_group; \
			else \
				about_group = "  " paint(dim, about_group); \
			printf "\n  %s %s%s\n", paint(col[group], "■"), \
				paint(col[group], sprintf("%-" (width + 3) "s", group)), about_group; \
			last = 0; \
			for (i = 1; i <= total; i++) if (owner[i] == group) last = i; \
			for (i = 1; i <= total; i++) \
				if (owner[i] == group) \
					printf "    %s %s  %s\n", paint(col[group], i == last ? "└─" : "├─"), \
						paint(bold, sprintf("%-" width "s", name[i])), hint(about[i]) \
		} \
		printf "\n%s\n", rule(); \
		if (only == "") { \
			usage("make <group>", "run its default (→), or list its commands"); \
			usage("make <group> <cmd...>", "run one or more commands in order"); \
			usage("NO_COLOR=1", "plain output; FORCE_COLOR=1 keeps colour when piped") \
		} else { \
			for (i = 1; i <= total; i++) if (owner[i] == only) { example = name[i]; break } \
			usage("make " only " " example, "run a command; several run in order"); \
			usage("make", "every group") \
		} \
		print "" \
	}' $(firstword $(MAKEFILE_LIST))

TARGETS := help $(GROUPS) $(addsuffix .default,$(RUNNABLE)) \
	$(shell sed -nE 's/^\#\# ([a-z]+\.[a-z0-9-]+):.*/\1/p' $(firstword $(MAKEFILE_LIST)))

.PHONY: $(TARGETS)

