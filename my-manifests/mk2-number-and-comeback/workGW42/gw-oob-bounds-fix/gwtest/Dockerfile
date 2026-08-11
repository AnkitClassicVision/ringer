ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN if command -v apt-get >/dev/null 2>&1; then \
      apt-get update && \
      apt-get install -y --no-install-recommends \
        ca-certificates curl gettext-base libnginx-mod-http-modsecurity \
        modsecurity-crs nginx openssl python3 python3-boto3 && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      echo "BASE_IMAGE must support apt-get or already include nginx, ModSecurity CRS, openssl, envsubst, and python3" >&2; \
      exit 1; \
    fi

# Tailscale (userspace networking, no TUN) so the gateway egresses EyeCloud traffic
# through a trusted office exit node — EyeCloud/PerimeterX blocks AWS datacenter IPs,
# so all eyecloud-pro CLI calls are routed (HTTPS_PROXY) through the exit node and
# appear to EyeCloud as the clinic's office IP. AWS API calls stay direct.
RUN curl -fsSL https://tailscale.com/install.sh | sh && \
    mkdir -p /var/lib/tailscale /var/run/tailscale

COPY container/bland_gateway.py /opt/cvc-booking-gateway/bland_gateway.py
COPY container/capability_registry.py /opt/cvc-booking-gateway/capability_registry.py
COPY container/eyecloud_capabilities.v1.json /opt/cvc-booking-gateway/eyecloud_capabilities.v1.json
COPY container/feed_task.py /opt/cvc-booking-gateway/feed_task.py
COPY container/session_warm.py /opt/cvc-booking-gateway/session_warm.py
COPY container/entrypoint.sh /opt/cvc-booking-gateway/entrypoint.sh
COPY container/cli_session_warm.sh /opt/cvc-booking-gateway/cli_session_warm.sh
COPY container/vendor/eyecloud-pro-pp-cli /usr/local/bin/eyecloud-pro-pp-cli
COPY container/vendor/conductor-gateway /usr/local/bin/conductor-gateway
COPY container/vendor/conductor-signer /usr/local/bin/conductor-signer
COPY container/nginx.conf.template /etc/nginx/templates/cvc_gateway.conf.template
COPY container/modsecurity.conf /etc/nginx/modsecurity.conf

RUN chmod +x /opt/cvc-booking-gateway/entrypoint.sh /opt/cvc-booking-gateway/cli_session_warm.sh /usr/local/bin/eyecloud-pro-pp-cli /usr/local/bin/conductor-gateway /usr/local/bin/conductor-signer && \
    mkdir -p /run/cvc-gateway /var/cache/nginx /var/log/nginx

ENV ECP_SHIM_HOST=127.0.0.1 \
    ECP_SHIM_PORT=8431 \
    ECP_SHIM_TEST_MODE=1 \
    ECP_SESSION_WARM_ENABLED=1 \
    ECP_SESSION_REFRESH_S=1800 \
    TLS_CERT_FILE=/run/cvc-gateway/tls.crt \
    TLS_KEY_FILE=/run/cvc-gateway/tls.key

EXPOSE 443
ENTRYPOINT ["/opt/cvc-booking-gateway/entrypoint.sh"]
