###########################################################

ifeq (,$(PLATFORM))
PLATFORM=$(UNION_PLATFORM)
endif

ifeq (,$(PLATFORM))
	$(error please specify PLATFORM, eg. PLATFORM=trimui make)
endif

###############################

# overrides shared by all cores

# Upstream melonDS has a generic Unix target, not Cannelloni platform targets.
# Passing e.g. platform=miyoomini otherwise selects its Windows fallback.
melonds_HASH = 66b5d2634cd0a79030562811e6e05f5532f800ba
melonds_ARCH = $(firstword $(subst -, ,$(shell $(CROSS_COMPILE)gcc -dumpmachine)))
melonds_MAKE = $(MAKE) platform=unix ARCH=$(subst aarch64,arm64,$(melonds_ARCH)) CC=$(CROSS_COMPILE)gcc CXX="$(CROSS_COMPILE)g++ -static-libgcc -static-libstdc++" AR=$(CROSS_COMPILE)ar HAVE_OPENGL=0 HAVE_OPENGLES3=0

desmume2015_HASH = 422b688009ccb9f2917c086a8fe79c8cecb030ae
desmume2015_BUILD_PATH = desmume2015/desmume
desmume2015_MAKE = $(MAKE) -f Makefile.libretro platform=unix CC=$(CROSS_COMPILE)gcc CXX="$(CROSS_COMPILE)g++ -static-libgcc -static-libstdc++" AR=$(CROSS_COMPILE)ar DESMUME_JIT=0 DESMUME_JIT_ARM=0

# C++17 support differs across official device toolchains. Both choices use
# minarch and the same OS menu; the core filename always identifies its build.
NDS_CORE := $(shell CROSS_COMPILE='$(CROSS_COMPILE)' sh ../../all/cores/select-nds-core.sh)
ifeq (,$(NDS_CORE))
$(error Unable to select an NDS core; check CROSS_COMPILE and the device C++ compiler)
endif
override CORES := $(filter-out melonds desmume2015,$(CORES)) $(NDS_CORE)

# commits after this one break save states (as of 20231025)
# gpsp_HASH = 1d1c719

###############################

# this logic was broken out from picoarch's all-in-one makefile

PATCH = git apply
PROCS = -j4

###############################

BUILD_ROOT=../../$(PLATFORM)/cores

define TEMPLATE=

$1_REPO ?= https://github.com/libretro/$(1)
$1_MAKE ?= make $(and $($1_MAKEFILE),-f $($1_MAKEFILE)) platform=$(PLATFORM) $($(1)_FLAGS)
$1_BUILD_PATH ?= $(1)

src/$(1):
	mkdir -p src
	cd src && git clone $(if $($1_HASH),,--depth 1) --recursive $$($(1)_REPO) $(1)
	$(if $($1_HASH),cd src/$$($1_BUILD_PATH) && git checkout $($1_HASH) && echo $($1_HASH),)

src/$(1)/.patched: src/$(1)
	(test ! -f patches/$(1).patch) || (test -f src/$(1)/.patched) || (cd src/$(1) && $(PATCH) -p1 < ../../patches/$(1).patch && touch .patched && true)

src/$(1)/.patched-all:
	(test ! -d ../../all/cores/patches/$(1)) || (test -f src/$(1)/.patched-all) || (cd src/$(1) && $(foreach patch, $(sort $(wildcard ../../all/cores/patches/$(1)/*.patch)), $(PATCH) -p1 < ../../$(patch) &&) touch .patched-all && true)
	

output/$(1)_libretro.so: src/$(1)/.patched src/$(1)/.patched-all
	mkdir -p output
	cd src/$$($1_BUILD_PATH) && $$($1_MAKE) $(PROCS)
	mv src/$$($1_BUILD_PATH)/$(if $($(1)_CORE),$($(1)_CORE),$(1)_libretro.so) ./output

clone-$(1): src/$(1)

status-$(1): src/$(1)
	cd src/$(1) && git show --oneline -s

patch-$(1): src/$(1)/.patched

clean-$(1):
	test ! -d src/$(1) || cd src/$$($1_BUILD_PATH) && $$($1_MAKE) clean
	rm -rf output/$(1)_libretro.so

$(1): output/$(1)_libretro.so

endef

###############################

all: cores

$(foreach CORE,$(sort $(CORES) melonds desmume2015),$(eval $(call TEMPLATE,$(CORE))))

.PHONY: nds
nds: $(NDS_CORE)

cores: $(foreach CORE,$(CORES),$(CORE))
	
clean: $(foreach CORE,$(CORES),clean-$(CORE))
	
nuke:
	rm -rf ./output
	rm -rf ./src
