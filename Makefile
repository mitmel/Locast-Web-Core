dest=$(shell basename $(shell readlink -f .))
../locast_web_core.tar.gz:
	tar --exclude $(dest)/locast_core.egg-info --exclude $(dest)/build --exclude $(dest)/.git* --exclude $(dest)/dist --exclude \*.swp --exclude \*\~ -C ../ -zcvf $@ $(dest)
