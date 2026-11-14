# V4 Security Model and Threat Model

## Assets

- Raw vibration and derived machine-health data (production intelligence).
- Per-device HMAC keys and the OTA signing key.
- Fleet model artifacts and rollout state.

## Trust boundaries

```
[Node] ==LoRa/ESP-NOW==> [Site gateway] ==MQTT/HTTP==> [Operator UI]
   |                          |
   +-- signed OTA <-----------+ (manifest server)
```

The node trusts: its own NVS key, the signed OTA manifest. It does not trust
the radio channel. The gateway trusts the broker network and the operator
identity provider; it validates every frame independently.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Eavesdropping on LoRa | Payload contains features, not raw samples; optional AES-CCM link encryption can be layered on the same frame. |
| Frame forgery | 8-byte truncated HMAC-SHA256 per frame with a per-device key. |
| Replay | Monotonic `seq` stored in NVS; gateway rejects `seq <= last_seq`. |
| Device cloning | Unique keys injected at prodtest; secure boot + flash encryption protect key extraction. |
| Malicious OTA | HMAC-signed manifest, SHA-256 of the image, `min_version` anti-downgrade, pending-verify rollback. |
| Gateway spoofing | mTLS between bridge/gateway and broker in production (`mosquitto` listener 8883); API behind the operator VPN. |
| Key leakage | Keys never leave NVS/HSM; prodtest wipes and locks debug access; OTA key kept in an offline signer/HSM. |
| Denial of service | Queue-depth limits, frame-length/CRC checks, per-device rate limiting at the gateway. |
| Model poisoning / bad rollout | Operator approval, staged 10%→50%→100% rollout, alarm-rate auto-rollback. |
| Unauthorized maintenance suppression | Maintenance windows are authenticated operator actions and audited in the alerts table. |

## Secure boot and flash encryption

On pilot units, enable ESP32-S3 Secure Boot v2 and flash encryption before
shipping:

1. Generate the RSA-3072 signing key on an offline machine; store it in an HSM.
2. `idf.py secure-boot-v2` with the public key digest; burn the digest once.
3. Enable `CONFIG_SECURE_FLASH_ENC_ENCRYPTION` + release mode and encrypt the
   factory image.
4. Verify that UART download mode is disabled and the eFuse summary matches the
   build record.
5. Inject the per-device key in prodtest, then set the NVS read-protection flag.

Never commit private keys. The bench key in `v4_config.h` is for tests only.

## Gateway authentication

- Local/dev: HTTP on the private network.
- Pilot: TLS terminator (Caddy/nginx), operator login (OIDC or basic auth at the
  reverse proxy), and MQTT over TLS with client certificates.
- Prometheus/Grafana are bound to localhost or the VPN only.

## Incident response

1. Revoke the affected device key in the gateway registry.
2. Roll back the active model stage with `POST /api/rollout/check` or set stage 0.
3. Re-key the node through prodtest; rotate the fleet key if compromise is
   suspected at the factory.
4. Export the alerts/windows tables for forensics before pruning the database.
