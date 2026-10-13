#include <stdio.h>
#include <signal.h>
#include <string.h>
#include <msettings.h>

#include "defines.h"
#include "api.h"
#include "utils.h"

static volatile sig_atomic_t interrupted = 0;
static void stop_message(int signal_number) {
	(void)signal_number;
	interrupted = 1;
}

int main(int argc , char* argv[]) {
	
	if (argc < 2) return EXIT_FAILURE;
	const char* status_file = argc == 3 && !strcmp(argv[1], "--status-file") ? argv[2] : NULL;
	char msg[1024] = "Please wait...";
	if (!status_file) snprintf(msg, sizeof(msg), "%s", argv[1]);
	signal(SIGTERM, stop_message);
	signal(SIGINT, stop_message);
	signal(SIGHUP, stop_message);
	
	PWR_setCPUSpeed(CPU_SPEED_MENU);
	
	InitSettings();
	SDL_Surface* screen = GFX_init(MODE_MAIN);
	PAD_init();
	PWR_init();
	
	SDL_Event event;
	int quit = 0;
	
	int dirty = 1;
	uint32_t last_read = 0;
	while(!quit && !interrupted) {
		uint32_t frame_start = SDL_GetTicks();
		if (status_file && (!last_read || frame_start - last_read >= 250)) {
			FILE* status = fopen(status_file, "r");
			if (!status) break;
			char updated[sizeof(msg)];
			size_t length = fread(updated, 1, sizeof(updated) - 1, status);
			updated[length] = '\0';
			fclose(status);
			if (strcmp(updated, msg)) {
				memcpy(msg, updated, length + 1);
				dirty = 1;
			}
			last_read = frame_start;
		}
		
		PAD_poll();
		if (!status_file && (PAD_justPressed(BTN_A) || PAD_justPressed(BTN_B))) {
			quit = 1;
		}
		
		// PWR_update(&dirty, NULL, NULL,NULL);
		
		if (dirty) {
			GFX_clear(screen);
			
			GFX_blitMessage(font.large, msg, screen,&(SDL_Rect){0,0,screen->w,screen->h-SCALE1(PADDING + PILL_SIZE + PADDING)});
			if (!status_file) GFX_blitButtonGroup((char*[]){ "A","OKAY", NULL }, 1, screen, 1);
			
			GFX_flip(screen);
			dirty = 0;
		}
		else GFX_sync();
	}
	
	QuitSettings();
	PWR_quit();
	PAD_quit();
	GFX_quit();
	
	return EXIT_SUCCESS;
}
