"""Exercise the actual launcher root so installed Settings paks stay reachable."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def function(source, name):
    match = re.search(r"^(?:static )?[^\n]+\b" + name + r"\([^\n]*\)\s*\{.*?^\}", source, re.M | re.S)
    if not match:
        raise AssertionError(name)
    return match.group(0)


class LauncherSettingsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gcc"), "Native gcc is required")
    def test_settings_root_entry_and_simple_mode(self):
        source = (ROOT / "workspace/all/cannelloni/cannelloni.c").read_text()
        utils = (ROOT / "workspace/all/common/utils.c").read_text()
        array = source[source.index("typedef struct Array {"):source.index("static void Array_push")]
        harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <dirent.h>
#define SDCARD_PATH "/sd"
#define PLATFORM "miyoomini"
#define ROMS_PATH "/sd/Roms"
#define COLLECTIONS_PATH "/sd/Collections"
#define FAUX_RECENT_PATH "/sd/Recently Played"
#define ENTRY_DIR 1
static int simple_mode, settings_present;
static int exists(char *path) { return settings_present && !strcmp(path, "/sd/Settings/miyoomini"); }
static int hasRecents(void) { return 0; }
static int hasCollections(void) { return 0; }
static int hasRoms(char *path) { (void)path; return 0; }
static void normalizeNewline(char *line) { (void)line; }
static void trimTrailingNewlines(char *line) { (void)line; }
typedef int Hash;
static Hash *Hash_new(void) { return NULL; }
static void Hash_set(Hash *h, char *a, char *b) { (void)h; (void)a; (void)b; }
static char *Hash_get(Hash *h, char *a) { (void)h; (void)a; return NULL; }
static void Hash_free(Hash *h) { (void)h; }
typedef struct Entry { char *path, *name, *unique; int type, alpha; } Entry;
''' + array + "\n" + "\n".join(function(utils, name) for name in
          ("suffixMatch", "exactMatch", "hide", "getDisplayName")) + "\n" + "\n".join(
            function(source, name) for name in ("Array_push", "Array_free", "Entry_new", "Entry_free",
                                                "EntryArray_sortEntry", "EntryArray_sort", "EntryArray_free", "getRoot")) + r'''
int main(void) {
    settings_present = 1;
    Array *root = getRoot();
    assert(root->count == 1);
    Entry *settings = root->items[0];
    assert(!strcmp(settings->name, "Settings"));
    assert(!strcmp(settings->path, "/sd/Settings/miyoomini"));
    assert(settings->type == ENTRY_DIR);
    EntryArray_free(root);
    simple_mode = 1;
    root = getRoot(); assert(root->count == 0); EntryArray_free(root);
    simple_mode = 0; settings_present = 0;
    root = getRoot(); assert(root->count == 0); EntryArray_free(root);
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="launcher settings ") as directory:
            code = Path(directory) / "harness.c"
            code.write_text(harness)
            binary = Path(directory) / "harness.exe"
            result = subprocess.run([shutil.which("gcc"), "-std=gnu99", str(code), "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
