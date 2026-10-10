# Password-protected judge access

The submitted browser demo uses the judge deployment described by `infra-judges.json`. `infra.json` is the earlier IAM-only alternative, not the submitted browser access arrangement. Code alone is not proof of deployment; dated HTTP checks and configuration evidence are distinguished below.

## Submission and access verification — 10 October 2026

Devpost submission 1228958 for [CaptureGate](https://devpost.com/software/capturegate) shows **Submitted, 5/5 steps done**. The additional-information page explicitly states that these fields are for judges and organizers and do not appear publicly unless noted. **Testing instructions** contains the demo URL and credentials; the stored password was compared privately with the working credential and matched. The **Working web endpoint** field contains the URL below. No password or password hash is included in this repository.

Live recheck: unauthenticated root, JavaScript, health and analysis-route requests returned 401; wrong credentials returned 401. Authenticated health returned OpenCV 5.0.0 and policy `capturegate-v0.9-manual-borders`. Authenticated HTML, JavaScript and CSS returned 200 and matched source bytes. Two authenticated fictional analyses returned `review_ready` for clean and `retake` for missing page. These two calls consume allowance; no exhaustion test was performed. Subsequent read-only AWS checks confirmed the recorded image digest, required auth, expiry, IAM-only direct URL, throttling and 1,000-attempt limit. The counter showed 4 used / 996 remaining at verification; see [audit](AUDIT_2026-10-10.md). No access settings were changed during this audit.

## Verified deployment — 8 October 2026

Endpoint: https://yq4tqjkm2f.execute-api.us-east-1.amazonaws.com

Historical deployment checks confirmed 401 for unauthenticated root, assets, health and analysis routes, and for a wrong password. Correct credentials loaded byte-matched JavaScript and processed clean and missing-page fictional fixtures with `review_ready` and `retake` respectively. The configuration receipt recorded direct Function URL authentication AWS_IAM, a lifetime allowance of 1,000 total analysis attempts including verification, and expiry 11 November 2026 at 00:00 UTC. Credential delivery was pending then; it is now verified above. This historical deployment receipt is not itself a competition submission receipt.

## Reproduction and security contract

The following are deployment instructions, not outstanding tasks for judges:

- Every route requires HTTPS Basic authentication in judge mode. Username is `judges`; generate a high-entropy random password, never reuse a personal password.
- Set `CAPTUREGATE_JUDGE_AUTH=required`, the password's SHA-256 and expiry through the template parameters. CloudFormation masks the hash parameter; plaintext must not enter source control, public descriptions, screenshots, logs or URL query strings.
- Invalid credentials return401, missing configuration503, and expired access403. Authentication runs before analysis and allowance consumption. An API Gateway request without configured judge auth fails closed.
- The gateway targets the same Lambda service. The direct Function URL retains AWS_IAM.
- DynamoDB atomically caps total analysis attempts at1000. Gateway throttling is1request/sec with burst10. These are not guaranteed currency caps; denied traffic and storage still have costs.
- Default expiry is11November2026 00:00UTC. Access expiration does not delete resources or stop storage charges.
- Before connecting the gateway, first deploy and verify authentication on the private function. Only then add the gateway. Never connect an older unprotected handler.
- Give the URL and credentials only through a verified private judge-access field or an organizer-approved private channel. A public repository/video is not a place for the password.

Test locally with `python -m unittest -v test_judge_auth`. For deployment verify unauthenticated requests to root, assets, health and analysis return401; wrong credentials return401; correct credentials load the exact UI and successfully process fictional fixtures. Do not exhaust the live allowance to test its limit; use the unit tests for that boundary.
