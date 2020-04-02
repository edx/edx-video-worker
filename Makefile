PACKAGES = video_worker

validate: test ## Run tests and quality checks

test: clean
	 nosetests --with-coverage --cover-inclusive --cover-branches \
		--cover-html --cover-html-dir=build/coverage/html/ \
		--cover-xml --cover-xml-file=build/coverage/coverage.xml --verbosity=2 \
		$(foreach package,$(PACKAGES),--cover-package=$(package)) \
		$(PACKAGES)

clean:
	coverage erase

quality:
	pep8 --config=.pep8 $(PACKAGES) *.py
	pylint --rcfile=pylintrc $(PACKAGES) *.py

piptools: ## install pinned version of pip-compile and pip-sync
	pip install -r requirements/pip-tools.txt

requirements: piptools ci_requirements ## sync to default requirements

ci_requirements: validation_requirements ## sync to requirements needed for CI checks

dev_requirements: ## sync to requirements for local development
	pip-sync -q requirements/dev.txt

validation_requirements: piptools ## sync to requirements for testing & code quality checking
	pip-sync -q requirements/travis.txt

doc_requirements:
	pip-sync -q requirements/doc.txt

prod_requirements: ## install requirements for production
	pip-sync -q requirements/production.txt

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: piptools ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	# Make sure to compile files after any other files they include!
	pip-compile --upgrade -o requirements/pip-tools.txt requirements/pip-tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/dev.txt requirements/dev.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	pip-compile --upgrade -o requirements/travis.txt requirements/travis.in
	pip-compile --upgrade -o requirements/production.txt requirements/production.in
