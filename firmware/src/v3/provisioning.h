#pragma once

// SoftAP captive portal used when no Wi-Fi credentials are stored (or when the
// provisioning button is held at boot). Saves credentials to NVS, then reboots.
void provisioning_start();
void provisioning_loop();
bool provisioning_active();
