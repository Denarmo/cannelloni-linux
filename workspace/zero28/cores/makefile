all:
	# copy from trimui smart pro (for now?)
	rm -rf output
	cp -r ../../tg5040/cores/output ./
	rm -f output/melonds_libretro.so output/desmume2015_libretro.so
	$(MAKE) nds

.PHONY: nds melonds desmume2015
nds melonds desmume2015:
	$(MAKE) -f ../../all/cores/makefile CORES=melonds $@
