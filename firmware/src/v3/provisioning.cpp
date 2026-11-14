#include "provisioning.h"

#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>

namespace {

WebServer server(80);
bool active = false;

const char *kForm =
    "<!doctype html><meta name=viewport content='width=device-width'>"
    "<h2>VibeGuard setup</h2><form method=post action=/save>"
    "SSID <input name=ssid><br>Password <input name=pass type=password><br>"
    "Device ID <input name=id value='node-01'><br>"
    "<button>Save</button></form>";

} // namespace

bool provisioning_active() { return active; }

void provisioning_start() {
  if (active) return;
  WiFi.mode(WIFI_AP);
  WiFi.softAP("VibeGuard-Setup");
  server.on("/", HTTP_GET, [] { server.send(200, "text/html", kForm); });
  server.on("/save", HTTP_POST, [] {
    String ssid = server.arg("ssid");
    String pass = server.arg("pass");
    String id = server.arg("id");
    if (!ssid.length()) {
      server.send(400, "text/plain", "ssid required");
      return;
    }
    Preferences prefs;
    prefs.begin("vgwifi", false);
    prefs.putString("ssid", ssid);
    prefs.putString("pass", pass);
    if (id.length()) prefs.putString("device_id", id);
    // Clear fast-reconnect hints so the next boot does a clean scan.
    prefs.remove("ch");
    prefs.remove("bssid");
    prefs.remove("ip");
    prefs.remove("gw");
    prefs.remove("mask");
    prefs.end();
    server.send(200, "text/plain", "saved; rebooting");
    delay(500);
    ESP.restart();
  });
  server.onNotFound([] { server.send(200, "text/html", kForm); });
  server.begin();
  active = true;
}

void provisioning_loop() {
  if (active) server.handleClient();
}
