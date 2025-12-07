.PHONY: lint clean

init:
	cp template_env.sh env.sh
	@TOOLDIR=$$(pwd); \
	echo "export TOOLDIR=$$TOOLDIR" >> ~/.bashrc ; \
	echo "source $$TOOLDIR/toolbox.sh" >> ~/.bashrc
	@date > init

clean:
	@cp ~/.bashrc ./.bashrc
	@sed -i '/TOOLDIR/d;/toolbox\.sh/d' ~/.bashrc
	@rm ./init

lint:
	flake8 s.py	

