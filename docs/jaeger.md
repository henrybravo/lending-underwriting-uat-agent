# Jaeger Setup Guide

This guide shows how to run Jaeger All-in-One locally with OTLP enabled and a custom UI configuration file.

## Overview

- Image: `jaegertracing/all-in-one:latest`
- UI config mounted from `jaeger-ui-config.json`
- OTLP enabled (`COLLECTOR_OTLP_ENABLED=true`)
- Ports exposed: UI `16686`, OTLP gRPC `4317`, OTLP HTTP `4318`

## Prerequisites

- Docker installed and running
- A UI config file at `jaeger-ui-config.json` in the repo root (customize as needed)

## Run via Docker (All-in-One)

Mount your UI config and pass it to the query service:

```bash
# From the repo root
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 -p 4317:4317 -p 4318:4318 \
  -v "$PWD/jaeger-ui-config.json:/etc/jaeger/ui-config.json:ro" \
  jaegertracing/all-in-one:latest \
  --query.ui-config /etc/jaeger/ui-config.json
```

Notes:
- `-v ...:/etc/jaeger/ui-config.json:ro` mounts your local config as read-only.
- `--query.ui-config` tells Jaeger Query (serves the UI) to use that file.
- `COLLECTOR_OTLP_ENABLED=true` enables both OTLP receivers (ports `4317` and `4318`).

## Verify the UI Config

- Open the UI: http://localhost:16686
- Or check the config endpoint:

```bash
curl -s http://localhost:16686/api/ui/config | jq .
```

## Query Traces via Standalone CLI Tool

The project includes a Jaeger Query CLI tool for programmatic trace access:

```bash
# List all services sending traces
python jaeger_mcp_server.py list-services

# Search traces by service
python jaeger_mcp_server.py search-traces fsi-lending-uat-agent --limit=5

# Get full trace details
python jaeger_mcp_server.py get-trace 19fd0ee263e03cfa8531e96e3ad71bfb

# Get detailed span information
python jaeger_mcp_server.py get-spans 19fd0ee263e03cfa8531e96e3ad71bfb

# Filter spans by operation
python jaeger_mcp_server.py get-spans 19fd0ee263e03cfa8531e96e3ad71bfb --filter="Tool:"
```

**Commands:**

- `list-services` – List all services sending traces
- `search-traces <service> [--limit=N] [--min-duration=ms] [--max-duration=ms]` – Find traces by service and duration
- `get-trace <trace-id>` – Retrieve full trace with all spans and operations
- `get-spans <trace-id> [--filter=<operation>]` – View detailed span table with metrics

**Example output:**
```
# Services in Jaeger

1. jaeger-all-in-one
2. fsi-lending-uat-agent

# Traces for service: fsi-lending-uat-agent

Found 5 trace(s):

- Trace ID: `19fd0ee263e03cfa8531e96e3ad71bfb`
  Spans: 4, Duration: 143µs, Start: 01:00:00 UTC
```

The tool works standalone (no MCP required) but can be wrapped into an MCP server for use with Claude or other AI clients.

## Query Traces via curl

If Jaeger is running, query directly:

**List services:**
```bash
curl -s http://localhost:16686/api/services | jq .data
```

**Search traces:**
```bash
curl -s "http://localhost:16686/api/traces?service=fsi-lending-uat-agent&limit=5" | jq .
```

**Get trace details:**
```bash
# Replace TRACE_ID with actual ID from search results
TRACE_ID="abc123"
curl -s "http://localhost:16686/api/traces/$TRACE_ID" | jq .data[0].spans
```

**Filter by duration (min 10ms):**
```bash
curl -s "http://localhost:16686/api/traces?service=fsi-lending-uat-agent&minDuration=10000" | jq .
```

## Theme Support (Light/Dark Mode)

Enable the theme toggle in the UI by adding this to `jaeger-ui-config.json`:

```json
{
  "themes": {
    "enabled": true
  }
}
```

Recreate the container to apply changes (see next section).

## Send Test Spans (Optional)

If you have an app using OTLP, point it at:
- OTLP gRPC: `http://localhost:4317`
- OTLP HTTP: `http://localhost:4318`

Example with `OTEL_EXPORTER_OTLP_ENDPOINT`:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Docker Compose Option

Create `docker-compose.yml` with:
```yaml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: jaeger
    ports:
      - "16686:16686"
      - "4317:4317"
      - "4318:4318"
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    volumes:
      - ./jaeger-ui-config.json:/etc/jaeger/ui-config.json:ro
    command: ["--query.ui-config=/etc/jaeger/ui-config.json"]
```

Run and verify:
```bash
docker compose up -d
curl -s http://localhost:16686/api/ui/config | jq .
```

## Advanced Settings

- Base path (behind reverse proxy):
```bash
# Add if serving behind /jaeger
-e QUERY_BASE_PATH=/jaeger
```
Update links in `jaeger-ui-config.json` accordingly if using a subpath.

- Common ports:
  - `16686`: Jaeger UI
  - `4317`: OTLP gRPC receiver
  - `4318`: OTLP HTTP receiver

## Troubleshooting

- UI config not applied:
  - Confirm volume mount path and `--query.ui-config` flag.
  - Check `curl http://localhost:16686/api/ui/config` returns your config.
- `jq: parse error: Invalid numeric literal` when curling `/api/ui/config`:
  - The endpoint likely returned non-JSON (e.g., HTML). Recreate the container with the config flag and mount:
    ```bash
    docker rm -f jaeger
    docker run -d --name jaeger \
      -e COLLECTOR_OTLP_ENABLED=true \
      -p 16686:16686 -p 4317:4317 -p 4318:4318 \
      -v "$PWD/jaeger-ui-config.json:/etc/jaeger/ui-config.json:ro" \
      jaegertracing/all-in-one:latest \
      --query.ui-config /etc/jaeger/ui-config.json
    ```
  - Verify inside the container:
    ```bash
    docker exec jaeger ls -l /etc/jaeger/ui-config.json
    docker exec jaeger cat /etc/jaeger/ui-config.json
    docker logs jaeger | tail -100
    ```
- Ports already in use: change host-side ports in `-p` mappings.
- No spans visible: ensure your app exports to `localhost:4317` or `:4318` and uses the correct protocol (gRPC vs HTTP).

## Clean Up

```bash
docker rm -f jaeger
```

## References

- Jaeger Deployment docs: https://www.jaegertracing.io/docs/latest/deployment/
- Jaeger Frontend/UI config: (served at `/api/ui/config` by Query)
- Image: https://hub.docker.com/r/jaegertracing/all-in-one
