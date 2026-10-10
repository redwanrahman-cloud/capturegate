# AWS deployment and reproduction

## Submitted deployment — status audited 10 October 2026

The competition entry includes https://yq4tqjkm2f.execute-api.us-east-1.amazonaws.com with credentials in private judge testing instructions. This is the API Gateway route from `infra-judges.json`, not an unauthenticated Function URL. HTTP access, authentication, exact UI assets and two synthetic analyses were reverified on 10 October. No redeployment or security-setting change was performed. Full live configuration and image digest were last recorded on 8 October; the current audit's AWS console session was expired. See [audit evidence](AUDIT_2026-10-10.md).

`infra-judges.json` defines HTTPS Basic authentication checked by Lambda before processing, expiry at 11 November 2026 00:00 UTC, a DynamoDB allowance of 1,000 total analysis attempts, and gateway throttling at 1 request/second with burst 10. The direct Function URL is AWS_IAM. Limits include verification attempts, do not guarantee a currency ceiling, and expiry does not stop ECR/log/storage charges. Never reset the allowance just to re-run tests. Preserve authentication, expiry and limits.

To reproduce the judge deployment in your own authorized account, review `infra-judges.json` and [JUDGE_ACCESS.md](JUDGE_ACCESS.md). Build the current Dockerfile (including readable source/static file modes), test it, and use an immutable image digest. Supply a new random credential hash and expiry securely, never through source control. Verify the authenticated private function before exposing the gateway; then verify unauthenticated rejection and authenticated access. This documentation is not permission to spend or deploy.

## Historical IAM-only pilot / optional private reproduction

Local testing needs no AWS. Cloud reproduction requires your own authorized account, Docker, AWS CLI and ECR repository, and can incur costs. Never paste credentials into source.

1. Build: `docker build --platform linux/amd64 -t capturegate:0.10 .`
2. Test: `docker run --rm --network none --entrypoint python -v "${PWD}:/work:ro" -w /work capturegate:0.10 -m unittest -v` (adjust mount syntax for your shell).
3. Authenticate to your own ECR using AWS CLI get-login-password piped into Docker password-stdin. Tag/push to your own repository.
4. Review and deploy infra.json using CloudFormation with ImageUri set to the pushed image digest and acknowledgment of IAM creation.
5. URL access is AWS_IAM only. Use authenticated Lambda invocation or a signed URL request; unauthenticated browsers are intentionally denied.
6. Invoke an API Gateway-v2-style event: rawPath /api/analyze, requestContext.http.method POST, content-type application/json, body `{"fixture":"clean"}`. Inspect statusCode/body and test failure fixtures from demo.py. GET /app.js should equal source bytes.

The steps above reproduce the IAM-only alternative; they do not create the submitted judge browser endpoint. The earlier screen-share-pending statement is superseded by the authenticated endpoint and private credential delivery. This guide does not authorize disabling authentication. Review unused resources in your own account when finished; storage and logs can consume credits even without public access.
