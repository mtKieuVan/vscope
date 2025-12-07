.PHONY: lint clean install-deps venv

VENV_DIR = .venv
PIP = $(VENV_DIR)/bin/pip
FLAKE8 = $(VENV_DIR)/bin/flake8

init:
	cp template_env.sh env.sh
	@TOOLDIR=$$(pwd); \
	echo "export TOOLDIR=$$TOOLDIR" >> ~/.bashrc ; \
	echo "source $$TOOLDIR/toolbox.sh" >> ~/.bashrc
	@date > init

clean:
	@cp ~/.bashrc ./.bashrc
	@sed -i '/TOOLDIR/d;/toolbox\.sh/d' ~/.bashrc
	@rm -f ./init
	rm -rf $(VENV_DIR)

venv:
	test -d $(VENV_DIR) || python -m venv $(VENV_DIR)

install-deps: venv
	$(PIP) install -r requirements.txt

lint: install-deps
	$(FLAKE8) s.py
