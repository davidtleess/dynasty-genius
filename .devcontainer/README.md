# Dynasty Genius Databricks Dev Container

This container is initialized for Databricks Asset Bundles, Unity Catalog feature-store work, MLflow evaluation gates, and Mosaic AI Agent deployment.

Required local environment variables are intentionally not committed:

- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN` or OAuth/service-principal fields
- `DATABRICKS_AUTH_TYPE`
- `ANTHROPIC_DATABRICKS_GATEWAY_URL` for the Azure/AWS Databricks Gateway
- `ANTHROPIC_BASE_URL` if the local client expects the generic Anthropic gateway variable
- `ANTHROPIC_AUTH_TOKEN` if required by the gateway
- `AWS_REGION` / `AWS_PROFILE` for AWS-hosted gateway auth, if applicable
- `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` for Azure gateway auth, if applicable

Validation commands:

```bash
databricks auth profiles
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

Security rule: secrets are inherited from the host shell only. They must never be written into `gen_alpha.bronze`, `gen_alpha.silver`, or source-controlled config.
