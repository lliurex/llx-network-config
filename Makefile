NO_COLOR    = \x1b[0m
BUILD_COLOR    = \x1b[32;01m
CLEAN_COLOR    = \x1b[31;01m


FILES:=$(patsubst src/%.svg,src/%.png,$(wildcard src/*.svg))
RENDERCMD=rsvg-convert

all: $(FILES)

src/%.png : src/%.svg
	@echo -e '$(BUILD_COLOR)* Rendering [$@]$(NO_COLOR)' 
	$(RENDERCMD) $< > $(patsubst src/%.png,%.png,$@)
	
	
clean:
	@echo -e '$(CLEAN_COLOR)* Cleaning...$(NO_COLOR)' 
	rm -rf $(patsubst src/%.svg,%.png,$(wildcard src/*.svg))
	
	