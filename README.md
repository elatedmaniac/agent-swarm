# MCP Platform with Hardened Ollama Container

This repository contains a security-hardened Docker configuration for running the Ollama model server alongside the MCP server application.

## Security Enhancements

The Docker image includes the following security improvements:

1. **System Updates**: All system packages are updated during build time
2. **Optional AppArmor Protection**: Custom AppArmor profile (if available on host)
3. **Non-root User**: The service runs as a non-privileged user
4. **Weekly Security Updates**: Cron job to update packages weekly
5. **Minimal Dependencies**: Only necessary packages are installed
6. **Least Privilege**: Dropped all unnecessary capabilities
7. **Read-only Filesystem**: Container runs with read-only root filesystem
8. **Process Isolation**: No new privileges flag prevents privilege escalation
9. **Health Monitoring**: Container health checks ensure service is running properly
10. **Log Management**: Log rotation to prevent disk space issues

### Security Configuration Notes

The current configuration uses `unconfined` for both AppArmor and seccomp settings to ensure maximum compatibility across different hosts. For enhanced security in production environments, consider:

1. Enabling the custom AppArmor profile by changing `apparmor=unconfined` to `apparmor=ollama` in docker-compose.yaml (requires AppArmor on the host)
2. Using the provided seccomp profile by changing `seccomp=unconfined` to `seccomp=./seccomp-profiles/default.json` (requires Docker with seccomp support)

## Running the Platform

The docker-compose file integrates both the cybersecurity model server and the MCP server:

```bash
docker-compose up -d
```

This will start both services:
- The cybersec-model service on port 11434
- The MCP server service on port 8000

## Project Structure

### Important Files

- `cybersec-agent/Modellfile`: Contains the configuration for the Ollama model (note the spelling with two 'l's)
- `cybersec-agent/Dockerfile`: Builds the hardened container for the cybersecurity model
- `cybersec-agent/apparmor-ollama`: AppArmor profile for the Ollama service
- `seccomp-profiles/default.json`: Custom seccomp profile for enhanced container security

## Verifying Security Status

### AppArmor Status (If Available)

If your system supports AppArmor and you've enabled it, you can check its status with:

```bash
docker exec -it mcp_cybersec-model_1 aa-status
```

### Enabling Enhanced Security

To enable the full security features (if your host supports them), edit the `docker-compose.yaml` file:

```yaml
security_opt:
  - apparmor=ollama  # Change from 'unconfined'
  - no-new-privileges=true
  - seccomp=./seccomp-profiles/default.json  # Change from 'unconfined'
```

## Security Best Practices

- Keep the container image up-to-date
- Monitor logs for unusual activity
- Use network isolation when deploying in production
- Set up proper user management for accessing the model
