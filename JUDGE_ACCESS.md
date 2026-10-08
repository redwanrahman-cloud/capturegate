# Password-protected judge access

`infra-judges.json` is an optional deployment, separate from the IAM-only template. Deployment status must be confirmed with a current receipt; code alone does not prove a running endpoint.

- Every route requires HTTPS Basic authentication in judge mode. Username is `judges`; generate a high-entropy random password, never reuse a personal password.
- Set `CAPTUREGATE_JUDGE_AUTH=required`, the password's SHA-256 and expiry through the template parameters. CloudFormation masks the hash parameter; plaintext must not enter source control, public descriptions, screenshots, logs or URL query strings.
- Invalid credentials return401, missing configuration503, and expired access403. Authentication runs before analysis and allowance consumption. An API Gateway request without configured judge auth fails closed.
- The gateway targets the same Lambda service. The direct Function URL retains AWS_IAM.
- DynamoDB atomically caps total analysis attempts at1000. Gateway throttling is1request/sec with burst10. These are not guaranteed currency caps; denied traffic and storage still have costs.
- Default expiry is11November2026 00:00UTC. Access expiration does not delete resources or stop storage charges.
- Before connecting the gateway, first deploy and verify authentication on the private function. Only then add the gateway. Never connect an older unprotected handler.
- Give the URL and credentials only through a verified private judge-access field or an organizer-approved private channel. A public repository/video is not a place for the password.

Test locally with `python -m unittest -v test_judge_auth`. For deployment verify unauthenticated requests to root, assets, health and analysis return401; wrong credentials return401; correct credentials load the exact UI and successfully process fictional fixtures. Do not exhaust the live allowance to test its limit; use the unit tests for that boundary.
