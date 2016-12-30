help:
	@echo "targets: autodoc, lint, runserver"

.PHONY: docs
docs:
	sphinx-apidoc -f -e -d 8 --doc-project=seqr --doc-author='seqr team' -o docs/ seqr/
	@cd docs && make html
	@echo Running docs server at: http://localhost:8080/
	@cd docs/_build/html && python2.7 -m SimpleHTTPServer 8080

#lint:
#       PyLint isn't well-integrated into IntelliJ or other IDEs, and must be run separately, so decided against using it
#	pylint --rcfile=.pylintrc seqr

.PHONY: test
test:
	python2.7 manage.py test

.PHONY: coverage
coverage:
	coverage run --source='.' manage.py test 

.PHONY: server
server:
	python2.7 manage.py runserver
