.PHONY: lint clean

init:
	@TOOLDIR=$$(pwd); \
	echo "export TOOLDIR=$$TOOLDIR" >> ~/.bashrc ; \
	echo "source $$TOOLDIR/toolbox.sh" >> ~/.bashrc
	@date > init

clean:
	@cp ~/.bashrc ./.bashrc
	@sed -i '/TOOLDIR/d;/toolbox\.sh/d' ~/.bashrc
	@rm ./init

lint:
	

