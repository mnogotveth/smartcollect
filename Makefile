PYTHON ?= python3
MANAGE := $(PYTHON) manage.py

.PHONY: install migrate runserver worker beat test shell createsuperuser format

install:
	$(PYTHON) -m pip install -r requirements.txt

migrate:
	$(MANAGE) migrate

runserver:
	$(MANAGE) runserver 0.0.0.0:8000

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info

test:
	$(MANAGE) test

shell:
	$(MANAGE) shell

createsuperuser:
	$(MANAGE) createsuperuser
