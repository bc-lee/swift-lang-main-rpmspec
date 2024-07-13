# Makefile for creating source RPMs for running in COPR
# See https://docs.pagure.org/copr.copr/user_documentation.html#make-srpm
# for more information
# Usage: make -f <cloned_repodir>/.copr/Makefile srpm outdir="<outdir>" spec="<spec_path>"

package_name := $(shell ls $(spec)/*.spec | xargs basename | cut -d. -f1)

.PHONY: prepare srpm

prepare:
	@echo "Installing tools..."
	@if command -v dnf5 >/dev/null 2>&1; then \
		pkg_manager=dnf5; \
	else \
		pkg_manager=dnf; \
	fi; \
	$$pkg_manager install -y rpm-build rpmdevtools || true
	@echo "Downloading sources..."
	spectool -g -R --define "_sourcedir $(spec)" $(spec)/$(package_name).spec

srpm: prepare
	@echo "Building SRPM..."
	rpmbuild -bs --define "_sourcedir $(spec)" --define "_srcrpmdir $(outdir)" $(spec)/$(package_name).spec
