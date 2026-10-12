#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <ifaddrs.h>
#include <pthread.h>
#include <time.h>
#include <ctype.h>

#include "defines.h"
#include "api.h"
#include "utils.h"

#define KITCHEN_DEFAULT_PORT 2121
#define KITCHEN_USER "cannelloni"
#define KITCHEN_PASS "cannelloni"
#define KITCHEN_STATUS_PATH "/tmp/kitchen.status"
#define KITCHEN_PID_PATH "/tmp/kitchen.pid"

static int server_running = 0;
static int server_port = KITCHEN_DEFAULT_PORT;
static char server_root[MAX_PATH] = SDCARD_PATH;
static pthread_t server_thread;

// Helper: get current local IP address
static void get_local_ip(char* out_ip, size_t max_len) {
	strncpy(out_ip, "127.0.0.1", max_len);
	
	// Try connecting UDP socket to determine route
	int s = socket(AF_INET, SOCK_DGRAM, 0);
	if (s >= 0) {
		struct sockaddr_in serv;
		memset(&serv, 0, sizeof(serv));
		serv.sin_family = AF_INET;
		serv.sin_addr.s_addr = inet_addr("8.8.8.8");
		serv.sin_port = htons(53);
		if (connect(s, (const struct sockaddr*)&serv, sizeof(serv)) == 0) {
			struct sockaddr_in name;
			socklen_t namelen = sizeof(name);
			if (getsockname(s, (struct sockaddr*)&name, &namelen) == 0) {
				const char* p = inet_ntop(AF_INET, &name.sin_addr, out_ip, max_len);
				if (p) {
					close(s);
					return;
				}
			}
		}
		close(s);
	}

	// Fallback: check network interfaces
	struct ifaddrs *ifaddr, *ifa;
	if (getifaddrs(&ifaddr) == -1) return;

	for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
		if (!ifa->ifa_addr || ifa->ifa_addr->sa_family != AF_INET) continue;
		if (strcmp(ifa->ifa_name, "lo") == 0) continue;
		struct sockaddr_in* pAddr = (struct sockaddr_in*)ifa->ifa_addr;
		inet_ntop(AF_INET, &pAddr->sin_addr, out_ip, max_len);
		break;
	}
	freeifaddrs(ifaddr);
}

// Client session structure
typedef struct {
	int ctrl_sock;
	int data_sock;
	int pasv_sock;
	struct sockaddr_in client_addr;
	struct sockaddr_in data_addr;
	int is_logged_in;
	char current_user[64];
	char cwd[MAX_PATH];
	long rest_offset;
	int mode_pasv;
	char rename_from[MAX_PATH];
} ClientSession;

static void send_resp(int sock, int code, const char* msg) {
	char buf[512];
	snprintf(buf, sizeof(buf), "%d %s\r\n", code, msg);
	send(sock, buf, strlen(buf), 0);
}

static void resolve_path(const char* cwd, const char* arg, char* out_path, size_t out_len) {
	char temp[MAX_PATH];
	if (arg[0] == '/') {
		snprintf(temp, sizeof(temp), "%s%s", server_root, arg);
	} else {
		snprintf(temp, sizeof(temp), "%s%s/%s", server_root, strcmp(cwd, "/") == 0 ? "" : cwd, arg);
	}

	// Simple canonicalization without leaving server_root
	char resolved[MAX_PATH];
	// Fallback to temp if realpath fails (e.g. target doesn't exist yet for STOR)
	if (!realpath(temp, resolved)) {
		strncpy(resolved, temp, sizeof(resolved) - 1);
		resolved[sizeof(resolved) - 1] = '\0';
	}
	// Check prefix
	if (strncmp(resolved, server_root, strlen(server_root)) != 0) {
		strncpy(out_path, server_root, out_len);
	} else {
		strncpy(out_path, resolved, out_len);
	}
}

static int open_data_conn(ClientSession* session) {
	if (session->mode_pasv) {
		if (session->pasv_sock < 0) return -1;
		struct sockaddr_in addr;
		socklen_t len = sizeof(addr);
		int ds = accept(session->pasv_sock, (struct sockaddr*)&addr, &len);
		close(session->pasv_sock);
		session->pasv_sock = -1;
		session->data_sock = ds;
		return ds;
	} else {
		int ds = socket(AF_INET, SOCK_STREAM, 0);
		if (ds < 0) return -1;
		if (connect(ds, (struct sockaddr*)&session->data_addr, sizeof(session->data_addr)) < 0) {
			close(ds);
			return -1;
		}
		session->data_sock = ds;
		return ds;
	}
}

static void handle_client(ClientSession* s) {
	char buf[1024];
	send_resp(s->ctrl_sock, 220, "Nonna's Kitchen FTP ready (Cannelloni)");

	while (server_running) {
		memset(buf, 0, sizeof(buf));
		int n = recv(s->ctrl_sock, buf, sizeof(buf) - 1, 0);
		if (n <= 0) break;
		buf[n] = '\0';

		// Trim \r\n
		while (n > 0 && (buf[n - 1] == '\r' || buf[n - 1] == '\n' || buf[n - 1] == ' ')) {
			buf[--n] = '\0';
		}
		if (n == 0) continue;

		char* cmd = buf;
		char* arg = strchr(buf, ' ');
		if (arg) {
			*arg = '\0';
			arg++;
			while (*arg == ' ') arg++;
		} else {
			arg = "";
		}

		// Convert command to uppercase
		for (char* p = cmd; *p; p++) *p = toupper((unsigned char)*p);

		if (strcmp(cmd, "USER") == 0) {
			strncpy(s->current_user, arg, sizeof(s->current_user) - 1);
			if (strcasecmp(arg, "anonymous") == 0 || strcasecmp(arg, KITCHEN_USER) == 0) {
				send_resp(s->ctrl_sock, 331, "Please specify the password.");
			} else {
				send_resp(s->ctrl_sock, 331, "User name okay, need password.");
			}
		} else if (strcmp(cmd, "PASS") == 0) {
			s->is_logged_in = 1;
			send_resp(s->ctrl_sock, 230, "Login successful. Welcome to Nonna's Kitchen!");
		} else if (strcmp(cmd, "QUIT") == 0) {
			send_resp(s->ctrl_sock, 221, "Goodbye!");
			break;
		} else if (!s->is_logged_in) {
			send_resp(s->ctrl_sock, 530, "Please login with USER and PASS.");
		} else if (strcmp(cmd, "PWD") == 0 || strcmp(cmd, "XPWD") == 0) {
			char msg[MAX_PATH + 32];
			snprintf(msg, sizeof(msg), "\"%s\" is the current directory", s->cwd);
			send_resp(s->ctrl_sock, 257, msg);
		} else if (strcmp(cmd, "CWD") == 0 || strcmp(cmd, "XCWD") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			struct stat st;
			if (stat(target, &st) == 0 && S_ISDIR(st.st_mode)) {
				const char* rel = target + strlen(server_root);
				if (strlen(rel) == 0) rel = "/";
				strncpy(s->cwd, rel, sizeof(s->cwd) - 1);
				send_resp(s->ctrl_sock, 250, "Directory successfully changed.");
			} else {
				send_resp(s->ctrl_sock, 550, "Failed to change directory.");
			}
		} else if (strcmp(cmd, "CDUP") == 0 || strcmp(cmd, "XCUP") == 0) {
			char* p = strrchr(s->cwd, '/');
			if (p && p != s->cwd) {
				*p = '\0';
			} else {
				strcpy(s->cwd, "/");
			}
			send_resp(s->ctrl_sock, 250, "Directory changed to parent.");
		} else if (strcmp(cmd, "TYPE") == 0) {
			send_resp(s->ctrl_sock, 200, "Type set to binary.");
		} else if (strcmp(cmd, "PASV") == 0) {
			if (s->pasv_sock >= 0) close(s->pasv_sock);
			s->pasv_sock = socket(AF_INET, SOCK_STREAM, 0);
			struct sockaddr_in paddr;
			memset(&paddr, 0, sizeof(paddr));
			paddr.sin_family = AF_INET;
			paddr.sin_addr.s_addr = INADDR_ANY;
			paddr.sin_port = 0;
			bind(s->pasv_sock, (struct sockaddr*)&paddr, sizeof(paddr));
			listen(s->pasv_sock, 1);

			socklen_t plen = sizeof(paddr);
			getsockname(s->pasv_sock, (struct sockaddr*)&paddr, &plen);
			int port = ntohs(paddr.sin_port);

			char local_ip[64];
			get_local_ip(local_ip, sizeof(local_ip));
			int a1, a2, a3, a4;
			sscanf(local_ip, "%d.%d.%d.%d", &a1, &a2, &a3, &a4);

			char resp[128];
			snprintf(resp, sizeof(resp), "Entering Passive Mode (%d,%d,%d,%d,%d,%d).",
			         a1, a2, a3, a4, port / 256, port % 256);
			s->mode_pasv = 1;
			send_resp(s->ctrl_sock, 227, resp);
		} else if (strcmp(cmd, "EPSV") == 0) {
			if (s->pasv_sock >= 0) close(s->pasv_sock);
			s->pasv_sock = socket(AF_INET, SOCK_STREAM, 0);
			struct sockaddr_in paddr;
			memset(&paddr, 0, sizeof(paddr));
			paddr.sin_family = AF_INET;
			paddr.sin_addr.s_addr = INADDR_ANY;
			paddr.sin_port = 0;
			bind(s->pasv_sock, (struct sockaddr*)&paddr, sizeof(paddr));
			listen(s->pasv_sock, 1);

			socklen_t plen = sizeof(paddr);
			getsockname(s->pasv_sock, (struct sockaddr*)&paddr, &plen);
			int port = ntohs(paddr.sin_port);

			char resp[64];
			snprintf(resp, sizeof(resp), "Entering Extended Passive Mode (|||%d|)", port);
			s->mode_pasv = 1;
			send_resp(s->ctrl_sock, 229, resp);
		} else if (strcmp(cmd, "PORT") == 0) {
			int h1, h2, h3, h4, p1, p2;
			if (sscanf(arg, "%d,%d,%d,%d,%d,%d", &h1, &h2, &h3, &h4, &p1, &p2) == 6) {
				char ip_str[32];
				snprintf(ip_str, sizeof(ip_str), "%d.%d.%d.%d", h1, h2, h3, h4);
				s->data_addr.sin_family = AF_INET;
				s->data_addr.sin_addr.s_addr = inet_addr(ip_str);
				s->data_addr.sin_port = htons(p1 * 256 + p2);
				s->mode_pasv = 0;
				send_resp(s->ctrl_sock, 200, "PORT command successful.");
			} else {
				send_resp(s->ctrl_sock, 501, "Syntax error in PORT.");
			}
		} else if (strcmp(cmd, "LIST") == 0 || strcmp(cmd, "NLST") == 0) {
			int ds = open_data_conn(s);
			if (ds < 0) {
				send_resp(s->ctrl_sock, 425, "Can't open data connection.");
				continue;
			}
			send_resp(s->ctrl_sock, 150, "Here comes the directory listing.");

			char target[MAX_PATH];
			resolve_path(s->cwd, (strlen(arg) > 0 && arg[0] != '-') ? arg : "", target, sizeof(target));
			DIR* dir = opendir(target);
			if (dir) {
				struct dirent* entry;
				while ((entry = readdir(dir)) != NULL) {
					if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
					char full[MAX_PATH];
					snprintf(full, sizeof(full), "%s/%s", target, entry->d_name);
					struct stat st;
					stat(full, &st);
					char line[512];
					if (strcmp(cmd, "NLST") == 0) {
						snprintf(line, sizeof(line), "%s\r\n", entry->d_name);
					} else {
						char timestr[64];
						struct tm* tm_info = localtime(&st.st_mtime);
						strftime(timestr, sizeof(timestr), "%b %d %H:%M", tm_info);
						snprintf(line, sizeof(line), "%s   1 owner group %10ld %s %s\r\n",
						         S_ISDIR(st.st_mode) ? "drwxr-xr-x" : "-rw-r--r--",
						         (long)st.st_size, timestr, entry->d_name);
					}
					send(ds, line, strlen(line), 0);
				}
				closedir(dir);
			}
			close(ds);
			s->data_sock = -1;
			send_resp(s->ctrl_sock, 226, "Directory send OK.");
		} else if (strcmp(cmd, "RETR") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			FILE* f = fopen(target, "rb");
			if (!f) {
				send_resp(s->ctrl_sock, 550, "Failed to open file.");
				continue;
			}
			int ds = open_data_conn(s);
			if (ds < 0) {
				fclose(f);
				send_resp(s->ctrl_sock, 425, "Can't open data connection.");
				continue;
			}
			send_resp(s->ctrl_sock, 150, "Opening BINARY mode data connection.");

			if (s->rest_offset > 0) {
				fseek(f, s->rest_offset, SEEK_SET);
				s->rest_offset = 0;
			}

			char chunk[8192];
			size_t r;
			while ((r = fread(chunk, 1, sizeof(chunk), f)) > 0) {
				send(ds, chunk, r, 0);
			}
			fclose(f);
			close(ds);
			s->data_sock = -1;
			send_resp(s->ctrl_sock, 226, "Transfer complete.");
		} else if (strcmp(cmd, "STOR") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			FILE* f = fopen(target, s->rest_offset > 0 ? "r+b" : "wb");
			if (!f && s->rest_offset > 0) f = fopen(target, "wb");
			if (!f) {
				send_resp(s->ctrl_sock, 550, "Cannot create file.");
				continue;
			}
			int ds = open_data_conn(s);
			if (ds < 0) {
				fclose(f);
				send_resp(s->ctrl_sock, 425, "Can't open data connection.");
				continue;
			}
			send_resp(s->ctrl_sock, 150, "Ready to receive data.");

			if (s->rest_offset > 0) {
				fseek(f, s->rest_offset, SEEK_SET);
				s->rest_offset = 0;
			}

			char chunk[8192];
			int r;
			while ((r = recv(ds, chunk, sizeof(chunk), 0)) > 0) {
				fwrite(chunk, 1, r, f);
			}
			fclose(f);
			close(ds);
			s->data_sock = -1;
			send_resp(s->ctrl_sock, 226, "Transfer complete.");
		} else if (strcmp(cmd, "DELE") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			if (unlink(target) == 0) {
				send_resp(s->ctrl_sock, 250, "File deleted.");
			} else {
				send_resp(s->ctrl_sock, 550, "Delete failed.");
			}
		} else if (strcmp(cmd, "RMD") == 0 || strcmp(cmd, "XRMD") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			if (rmdir(target) == 0) {
				send_resp(s->ctrl_sock, 250, "Directory removed.");
			} else {
				send_resp(s->ctrl_sock, 550, "Remove directory failed.");
			}
		} else if (strcmp(cmd, "MKD") == 0 || strcmp(cmd, "XMKD") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			if (mkdir(target, 0755) == 0) {
				send_resp(s->ctrl_sock, 257, "Directory created.");
			} else {
				send_resp(s->ctrl_sock, 550, "Create directory failed.");
			}
		} else if (strcmp(cmd, "RNFR") == 0) {
			resolve_path(s->cwd, arg, s->rename_from, sizeof(s->rename_from));
			send_resp(s->ctrl_sock, 350, "File exists, ready for destination name.");
		} else if (strcmp(cmd, "RNTO") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			if (rename(s->rename_from, target) == 0) {
				send_resp(s->ctrl_sock, 250, "Rename successful.");
			} else {
				send_resp(s->ctrl_sock, 550, "Rename failed.");
			}
		} else if (strcmp(cmd, "SIZE") == 0) {
			char target[MAX_PATH];
			resolve_path(s->cwd, arg, target, sizeof(target));
			struct stat st;
			if (stat(target, &st) == 0) {
				char msg[64];
				snprintf(msg, sizeof(msg), "%ld", (long)st.st_size);
				send_resp(s->ctrl_sock, 213, msg);
			} else {
				send_resp(s->ctrl_sock, 550, "Could not get file size.");
			}
		} else if (strcmp(cmd, "REST") == 0) {
			s->rest_offset = atol(arg);
			send_resp(s->ctrl_sock, 350, "Restarting transfer.");
		} else if (strcmp(cmd, "FEAT") == 0) {
			send(s->ctrl_sock, "211-Features:\r\n UTF8\r\n REST STREAM\r\n SIZE\r\n211 End\r\n", 53, 0);
		} else if (strcmp(cmd, "OPTS") == 0) {
			send_resp(s->ctrl_sock, 200, "OK");
		} else if (strcmp(cmd, "SYST") == 0) {
			send_resp(s->ctrl_sock, 215, "UNIX Type: L8");
		} else if (strcmp(cmd, "NOOP") == 0) {
			send_resp(s->ctrl_sock, 200, "NOOP ok.");
		} else {
			send_resp(s->ctrl_sock, 502, "Command not implemented.");
		}
	}

	if (s->pasv_sock >= 0) close(s->pasv_sock);
	if (s->data_sock >= 0) close(s->data_sock);
	close(s->ctrl_sock);
	free(s);
}

static void* client_thread_func(void* arg) {
	ClientSession* s = (ClientSession*)arg;
	handle_client(s);
	return NULL;
}

static void* server_listen_thread(void* arg) {
	int listen_sock = socket(AF_INET, SOCK_STREAM, 0);
	if (listen_sock < 0) return NULL;

	int opt = 1;
	setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

	struct sockaddr_in serv_addr;
	memset(&serv_addr, 0, sizeof(serv_addr));
	serv_addr.sin_family = AF_INET;
	serv_addr.sin_addr.s_addr = INADDR_ANY;
	serv_addr.sin_port = htons(server_port);

	if (bind(listen_sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
		close(listen_sock);
		return NULL;
	}

	listen(listen_sock, 5);

	// Write status file
	char local_ip[64];
	get_local_ip(local_ip, sizeof(local_ip));
	FILE* sf = fopen(KITCHEN_STATUS_PATH, "w");
	if (sf) {
		fprintf(sf, "status=running\nip=%s\nport=%d\npid=%d\n", local_ip, server_port, getpid());
		fclose(sf);
	}
	FILE* pf = fopen(KITCHEN_PID_PATH, "w");
	if (pf) {
		fprintf(pf, "%d\n", getpid());
		fclose(pf);
	}

	while (server_running) {
		struct sockaddr_in cli_addr;
		socklen_t cli_len = sizeof(cli_addr);
		int cs = accept(listen_sock, (struct sockaddr*)&cli_addr, &cli_len);
		if (cs < 0) {
			if (!server_running) break;
			continue;
		}

		ClientSession* session = calloc(1, sizeof(ClientSession));
		session->ctrl_sock = cs;
		session->data_sock = -1;
		session->pasv_sock = -1;
		session->client_addr = cli_addr;
		strcpy(session->cwd, "/");

		pthread_t ct;
		pthread_create(&ct, NULL, client_thread_func, session);
		pthread_detach(ct);
	}

	close(listen_sock);
	unlink(KITCHEN_STATUS_PATH);
	unlink(KITCHEN_PID_PATH);
	return NULL;
}

void kitchen_start(void) {
	if (server_running) return;
	server_running = 1;
	pthread_create(&server_thread, NULL, server_listen_thread, NULL);
}

void kitchen_stop(void) {
	if (!server_running) return;
	server_running = 0;
	// Wake up accept
	int s = socket(AF_INET, SOCK_STREAM, 0);
	if (s >= 0) {
		struct sockaddr_in serv;
		memset(&serv, 0, sizeof(serv));
		serv.sin_family = AF_INET;
		serv.sin_addr.s_addr = inet_addr("127.0.0.1");
		serv.sin_port = htons(server_port);
		connect(s, (struct sockaddr*)&serv, sizeof(serv));
		close(s);
	}
	pthread_join(server_thread, NULL);
	unlink(KITCHEN_STATUS_PATH);
	unlink(KITCHEN_PID_PATH);
}

static void stop_existing_daemon(void) {
	FILE* pf = fopen(KITCHEN_PID_PATH, "r");
	if (pf) {
		int pid = 0;
		if (fscanf(pf, "%d", &pid) == 1 && pid > 0) {
			kill(pid, SIGTERM);
			usleep(100000);
		}
		fclose(pf);
	}
	unlink(KITCHEN_STATUS_PATH);
	unlink(KITCHEN_PID_PATH);
}

int main(int argc, char* argv[]) {
	int daemon_mode = 0;

	for (int i = 1; i < argc; i++) {
		if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--daemon") == 0) {
			daemon_mode = 1;
		} else if (strcmp(argv[i], "-k") == 0 || strcmp(argv[i], "--stop") == 0) {
			stop_existing_daemon();
			return 0;
		} else if (strcmp(argv[i], "-s") == 0 || strcmp(argv[i], "--status") == 0) {
			if (exists(KITCHEN_STATUS_PATH)) {
				char status[256];
				getFile(KITCHEN_STATUS_PATH, status, sizeof(status));
				printf("%s", status);
			} else {
				printf("status=stopped\n");
			}
			return 0;
		} else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
			server_port = atoi(argv[++i]);
		} else if (strcmp(argv[i], "-r") == 0 && i + 1 < argc) {
			strncpy(server_root, argv[++i], sizeof(server_root) - 1);
		}
	}

	if (!exists(server_root)) {
		strcpy(server_root, "/mnt/SDCARD");
		if (!exists(server_root)) {
			strcpy(server_root, "/storage/roms");
			if (!exists(server_root)) {
				strcpy(server_root, ".");
			}
		}
	}

	if (daemon_mode) {
		stop_existing_daemon();
		pid_t pid = fork();
		if (pid < 0) exit(EXIT_FAILURE);
		if (pid > 0) exit(EXIT_SUCCESS); // Parent exits

		setsid();
		kitchen_start();
		while (server_running) sleep(1);
		return 0;
	}

	// Interactive GUI Mode
	InitSettings();
	SDL_Surface* screen = GFX_init(MODE_MAIN);
	PAD_init();
	PWR_init();

	kitchen_start();

	int dirty = 1;
	int quit = 0;
	char ip_str[64];
	get_local_ip(ip_str, sizeof(ip_str));

	int online = PLAT_isOnline();

	while (!quit) {
		unsigned long now = SDL_GetTicks();
		PAD_poll();

		int show_setting = 0;
		PWR_update(&dirty, &show_setting, NULL, NULL);

		int cur_online = PLAT_isOnline();
		if (cur_online != online) {
			online = cur_online;
			get_local_ip(ip_str, sizeof(ip_str));
			dirty = 1;
		}

		if (PAD_justPressed(BTN_B) || PAD_tappedMenu(now) || PAD_justPressed(BTN_A)) {
			quit = 1;
			break;
		}

		if (dirty) {
			GFX_clear(screen);
			GFX_blitHardwareGroup(screen, show_setting);

			int cx = screen->w / 2;
			int y = SCALE1(30);

			// Title
			SDL_Surface* title = TTF_RenderUTF8_Blended(font.large, "Nonna's Kitchen", COLOR_ACCENT_CURRENT);
			SDL_BlitSurface(title, NULL, screen, &(SDL_Rect){cx - title->w / 2, y});
			y += title->h + SCALE1(6);
			SDL_FreeSurface(title);

			// Subtitle
			SDL_Surface* sub = TTF_RenderUTF8_Blended(font.small, "Wireless FTP File Transfer", COLOR_DARK_TEXT);
			SDL_BlitSurface(sub, NULL, screen, &(SDL_Rect){cx - sub->w / 2, y});
			y += sub->h + SCALE1(24);
			SDL_FreeSurface(sub);

			// Server info card
			char url[128];
			snprintf(url, sizeof(url), "ftp://%s:%d", ip_str, server_port);
			
			SDL_Surface* url_txt = TTF_RenderUTF8_Blended(font.large, url, COLOR_WHITE);
			SDL_BlitSurface(url_txt, NULL, screen, &(SDL_Rect){cx - url_txt->w / 2, y});
			y += url_txt->h + SCALE1(16);
			SDL_FreeSurface(url_txt);

			// Credentials
			char creds[128];
			snprintf(creds, sizeof(creds), "User: %s   Pass: %s", KITCHEN_USER, KITCHEN_PASS);
			SDL_Surface* creds_txt = TTF_RenderUTF8_Blended(font.medium, creds, COLOR_LIGHT_TEXT);
			SDL_BlitSurface(creds_txt, NULL, screen, &(SDL_Rect){cx - creds_txt->w / 2, y});
			y += creds_txt->h + SCALE1(12);
			SDL_FreeSurface(creds_txt);

			// Status indicator
			char stat_msg[128];
			if (online) {
				snprintf(stat_msg, sizeof(stat_msg), "Status: Online (Connected to Wi-Fi)");
			} else {
				snprintf(stat_msg, sizeof(stat_msg), "Status: Listening (Connect to Wi-Fi)");
			}
			SDL_Surface* stat_txt = TTF_RenderUTF8_Blended(font.small, stat_msg, online ? COLOR_ACCENT_CURRENT : COLOR_DARK_TEXT);
			SDL_BlitSurface(stat_txt, NULL, screen, &(SDL_Rect){cx - stat_txt->w / 2, y});
			y += stat_txt->h + SCALE1(16);
			SDL_FreeSurface(stat_txt);

			// Storage info
			char store_msg[MAX_PATH + 32];
			snprintf(store_msg, sizeof(store_msg), "Serving: %s", server_root);
			SDL_Surface* store_txt = TTF_RenderUTF8_Blended(font.tiny, store_msg, COLOR_DARK_TEXT);
			SDL_BlitSurface(store_txt, NULL, screen, &(SDL_Rect){cx - store_txt->w / 2, y});
			SDL_FreeSurface(store_txt);

			// Button hints
			GFX_blitButtonGroup((char*[]){ "B", "STOP & EXIT", NULL }, 0, screen, 1);

			GFX_flip(screen);
			dirty = 0;
		} else {
			GFX_sync();
		}
	}

	kitchen_stop();
	PWR_quit();
	PAD_quit();
	GFX_quit();
	QuitSettings();

	return 0;
}
