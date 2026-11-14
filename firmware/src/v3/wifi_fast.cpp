#include "wifi_fast.h"

#include <Preferences.h>
#include <WiFi.h>

namespace {
Preferences prefs;
}

bool wifi_credentials_saved() {
  prefs.begin("vgwifi", true);
  bool ok = prefs.getString("ssid", "").length() > 0;
  prefs.end();
  return ok;
}

bool wifi_fast_connect(uint32_t timeout_ms) {
  prefs.begin("vgwifi", true);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  int32_t channel = prefs.getInt("ch", 0);
  uint32_t ip = prefs.getUInt("ip", 0);
  uint32_t gw = prefs.getUInt("gw", 0);
  uint32_t mask = prefs.getUInt("mask", 0);
  uint8_t bssid[6];
  size_t blen = prefs.getBytes("bssid", bssid, sizeof(bssid));
  prefs.end();
  if (!ssid.length()) return false;

  WiFi.mode(WIFI_STA);
  if (ip && gw && mask) {
    WiFi.config(IPAddress(ip), IPAddress(gw), IPAddress(mask));
  }
  if (blen == sizeof(bssid) && channel > 0) {
    WiFi.begin(ssid.c_str(), pass.c_str(), uint8_t(channel), bssid, true);
  } else {
    WiFi.begin(ssid.c_str(), pass.c_str());
  }

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeout_ms) {
    delay(50);
  }
  if (WiFi.status() == WL_CONNECTED) {
    wifi_fast_store();
    return true;
  }
  return false;
}

bool wifi_fast_connected() { return WiFi.status() == WL_CONNECTED; }

void wifi_fast_store() {
  if (WiFi.status() != WL_CONNECTED) return;
  prefs.begin("vgwifi", false);
  prefs.putInt("ch", WiFi.channel());
  prefs.putBytes("bssid", WiFi.BSSID(), 6);
  prefs.putUInt("ip", uint32_t(WiFi.localIP()));
  prefs.putUInt("gw", uint32_t(WiFi.gatewayIP()));
  prefs.putUInt("mask", uint32_t(WiFi.subnetMask()));
  prefs.end();
}
