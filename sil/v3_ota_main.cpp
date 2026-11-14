// Host SIL: sign/verify the V3 OTA manifest policy and inspect firmware hashes.
#include <cstdio>
#include <string>

#include "vg_core/v3/ota_verify.h"
#include "vg_core/v3/sha256.h"
#include "v3_cli.h"

static bool read_file(const char *path, std::string &out) {
  FILE *f = std::fopen(path, "rb");
  if (!f) return false;
  char buf[8192];
  size_t n;
  while ((n = std::fread(buf, 1, sizeof(buf), f)) > 0) out.append(buf, n);
  std::fclose(f);
  return true;
}

int main(int argc, char **argv) {
  const char *path = vgcli::arg(argc, argv, "--firmware");
  if (!path) {
    std::fprintf(stderr, "--firmware is required\n");
    return 2;
  }
  std::string fw;
  if (!read_file(path, fw)) {
    std::fprintf(stderr, "cannot read %s\n", path);
    return 2;
  }

  uint8_t digest[32];
  vg::sha256(fw.data(), fw.size(), digest);
  char computed_sha[65];
  vg::hex_encode(digest, sizeof(digest), computed_sha);

  if (vgcli::flag(argc, argv, "--sha256-only")) {
    std::printf("%s\n", computed_sha);
    return 0;
  }

  uint32_t version =
      static_cast<uint32_t>(vgcli::iarg(argc, argv, "--version", 1));
  uint32_t min_version =
      static_cast<uint32_t>(vgcli::iarg(argc, argv, "--min-version", 0));
  uint32_t current_version =
      static_cast<uint32_t>(vgcli::iarg(argc, argv, "--current-version", 0));
  uint32_t size = static_cast<uint32_t>(
      vgcli::iarg(argc, argv, "--size", static_cast<long>(fw.size())));
  const char *sha = vgcli::arg(argc, argv, "--sha256");
  if (!sha) sha = computed_sha;

  if (vgcli::flag(argc, argv, "--print-canonical")) {
    char canonical[160];
    vg::ota_canonical(canonical, sizeof(canonical), version, min_version, size,
                      sha);
    std::printf("%s", canonical);
    return 0;
  }

  const char *key_hex = vgcli::arg(argc, argv, "--key-hex");
  const char *sig_hex = vgcli::arg(argc, argv, "--sig");
  if (!key_hex || !sig_hex) {
    std::fprintf(stderr, "--key-hex and --sig are required for verification\n");
    return 2;
  }
  uint8_t key[64];
  size_t key_len = 0;
  if (!vg::hex_decode(key_hex, key, sizeof(key), &key_len)) {
    std::fprintf(stderr, "bad --key-hex\n");
    return 2;
  }

  vg::OtaResult r =
      vg::ota_verify(current_version, version, min_version, size, sha, sig_hex,
                     fw.data(), fw.size(), key, key_len);
  std::printf("{\"result\":\"%s\",\"valid\":%s,\"code\":%d}\n",
              vg::ota_result_name(r), r == vg::OtaResult::Ok ? "true" : "false",
              static_cast<int>(r));
  return r == vg::OtaResult::Ok ? 0 : 1;
}
