help:
	@echo "targets: " 
	@grep '^[^[:space:]#.].*:' Makefile | sed s/#//

#.PHONY: server
devserver:   # start a dev server
	npm run start

.PHONY: build
build:     # run python tests
	npm run build

.PHONY: test
test:     # run python tests
	npm run test

.PHONY: coverage
coverage: # run code coverage
	coverage run --source='.' manage.py test 

