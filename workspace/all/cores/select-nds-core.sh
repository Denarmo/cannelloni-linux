#!/bin/sh
# Probe the actual cross compiler: GCC 6 and older cannot build melonDS's
# C++17 Teakra decoder. Keep those devices on a correctly named libretro core.
set -eu
: "${CROSS_COMPILE:?Source the device toolchain environment first}"
command -v "${CROSS_COMPILE}g++" >/dev/null
if printf '%s\n' '#include <tuple>' \
    'template<class... T> constexpr int sum(T... v) { return (v + ...); }' \
    'static_assert(sum(1,2)==3, "fold expressions");' \
    'int main() { auto [a,b] = std::make_tuple(1,2); return a+b; }' |
    "${CROSS_COMPILE}g++" -std=c++17 -x c++ -fsyntax-only - >/dev/null 2>&1; then
    echo melonds
else
    echo desmume2015
fi
