#pragma once
#include <cstdlib>
#include <cstring>

// Tiny flag parser shared by the V3 host test binaries. Accepts
// "--flag value" pairs and boolean "--flag" switches.
namespace vgcli {

inline const char *arg(int argc, char **argv, const char *name) {
  for (int i = 1; i + 1 < argc; i++)
    if (std::strcmp(argv[i], name) == 0) return argv[i + 1];
  return nullptr;
}

inline bool flag(int argc, char **argv, const char *name) {
  for (int i = 1; i < argc; i++)
    if (std::strcmp(argv[i], name) == 0) return true;
  return false;
}

inline float farg(int argc, char **argv, const char *name, float def) {
  const char *v = arg(argc, argv, name);
  return v ? static_cast<float>(std::atof(v)) : def;
}

inline long iarg(int argc, char **argv, const char *name, long def) {
  const char *v = arg(argc, argv, name);
  return v ? std::strtol(v, nullptr, 10) : def;
}

inline bool barg(int argc, char **argv, const char *name, bool def) {
  const char *v = arg(argc, argv, name);
  if (!v) return def;
  return std::strcmp(v, "1") == 0 || std::strcmp(v, "true") == 0 ||
         std::strcmp(v, "yes") == 0;
}

} // namespace vgcli
