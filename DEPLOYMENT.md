# Private AWS reproduction

Local testing needs no AWS. Cloud reproduction requires your own authorized account, Docker, AWS CLI and ECR repository, and can incur costs. Never paste credentials into source.

1. Build: `docker build --platform linux/amd64 -t capturegate:0.10 .`
2. Test: `docker run --rm --network none --entrypoint python -v "${PWD}:/work:ro" -w /work capturegate:0.10 -m unittest -v` (adjust mount syntax for your shell).
3. Authenticate to your own ECR using AWS CLI get-login-password piped into Docker password-stdin. Tag/push to your own repository.
4. Review and deploy infra.json using CloudFormation with ImageUri set to the pushed image digest and acknowledgment of IAM creation.
5. URL access is AWS_IAM only. Use authenticated Lambda invocation or a signed URL request; unauthenticated browsers are intentionally denied.
6. Invoke an API Gateway-v2-style event: rawPath /api/analyze, requestContext.http.method POST, content-type application/json, body `{"fixture":"clean"}`. Inspect statusCode/body and test failure fixtures from demo.py. GET /app.js should equal source bytes.

Judge screen-share arrangement is pending, not a claimed public link. This guide does not authorize disabling authentication. Review/remove unused resources in your own account when finished; storage and logs can consume credits even without public access.
