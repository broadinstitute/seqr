help:
	@echo "targets: " 
	@grep '^[^[:space:]#.].*:' Makefile | sed s/#//

.PHONY: server
devserver:   # start a dev server
	python2.7 manage.py runserver

.PHONY: docs
docs:     # generate sphinx docs
	sphinx-apidoc -f -e -d 8 --doc-project=seqr --doc-author='seqr team' -o docs/ seqr/
	@cd docs && make html
	@echo Running docs server at: http://localhost:8080/
	@cd docs/_build/html && python2.7 -m SimpleHTTPServer 8080

#lint:
#       PyLint isn't well-integrated into IntelliJ or other IDEs, and must be run separately, so decided against using it
#	pylint --rcfile=.pylintrc seqr

.PHONY: test
test:     
	python2.7 -Wmodule -u manage.py test -p '*_tests.py' -v 2

.PHONY: coverage
coverage: # run code coverage
	coverage run --source='.' manage.py test 

