# CaptureGate technical report — submitted source, audited 10 October 2026

Application checkpoint: public source commit `93e184836d2110b87f38f92624f327bd1c8bb39f`, including authentication introduced in `861cadf` and the container-permission correction in `5084300`. This documentation correction does not change application behavior. The v0.10 handoff UI, `capturegate-v0.9-manual-borders` detector-policy identifier and `judges-v011r1` deployment image label describe different components/checkpoints, not contradictory detector releases. The policy identifier is still present in source and live health responses; it is not a source commit or model-accuracy certification.

## Problem and implementation
People handing document photographs into another workflow need useful framing, retake advice and control when automatic cropping fails. No medical, employment, identity or legal decisions are made. Benefit and willingness to pay remain unmeasured.

Pinned OpenCV 5.0.0.93 and NumPy 2.3.5 run in Python. vision.py resizes/smooths images, applies several Canny thresholds, morphological closing and convex quadrilateral filtering. Candidate sides require lighter-paper support. Laplacian detail and bright-region signals are measured inside a candidate. Unsupported boundaries abstain. rectify.py and page_crop.py support perspective warping; recovery.py provides natural, LAB-luminance contrast and adaptive black-and-white output, bounded to a 1200-pixel long side without upsampling. Manual geometry uses original pixels and is validated. Gentle sharpening changes contrast, not missing detail.

## Human review
Original findings remain separate from proposals. Crop-loss shading shows excluded regions. Changes invalidate acceptance; asynchronous export checks prevent stale approval reuse. A ZIP binds the actual reviewed JPEG bytes to JSON through SHA-256 and includes readable warnings. Hashing detects mismatch; it is not an authenticity signature. Manual approval never certifies whole-page completeness.

## AWS and evidence
The submitted demo uses an HTTPS API Gateway feeding the shared x86_64 Lambda/ECR service. `infra-judges.json` specifies application-level Basic authentication, expiry, a DynamoDB atomic analysis allowance, gateway throttling, 1024 MB, a 15-second Lambda timeout and three-day logs. The direct Function URL remains a separate AWS_IAM route according to the 8 October configuration receipt. `infra.json` describes the earlier IAM-only pilot. There is no pending screen-share requirement for the submitted endpoint arrangement. See [judge access](JUDGE_ACCESS.md) and [deployment](DEPLOYMENT.md).

### Test and deployment chronology

| Checkpoint | Evidence and scope |
| --- | --- |
| 8 October, v0.10 IAM-only pilot | Historical report: 67 Linux Python tests, seven generated Lambda checks, 46 local controller tests. Image digest `sha256:e7c7ce3f7f3f3b51210035e2299ca56edf72b0b8becfef1b5548883419b1067b`. This is not the later judge image. The optional allowance was not enabled in this earlier pilot. |
| 8 October, authenticated judge deployment | Eight authentication tests added by `861cadf` raised the Python suite to 75. Historical Linux run passed 75 tests. File permissions were repaired and a restricted-user smoke check passed before opening the gateway. Recorded working image digest `sha256:56d4a48ce2a847a572ce172f1659700b17c3f8b99b873f5f1a32ccaf5d1cd209`; template includes the DynamoDB allowance. Eight recorded HTTP checks passed. |
| 10 October, documentation audit | Current unchanged source: 75/75 Python tests on Windows Python 3.12.14, OpenCV wheel 5.0.0.93 (runtime 5.0.0), NumPy 2.3.5; 46/46 simulated-DOM controller tests; six geometry cases and 36/36 procedural regressions passed. Authenticated live clean/missing fixtures passed; invalid credentials rejected; all three served UI assets match source. No new Linux run or fresh ECR digest verification claimed. |

Live JavaScript SHA-256 rechecked 10 October: `011d00c775437d88f69323ccd32b3859e5f932eb8b144f08c8a73349047d0df6`. Asset equality and a policy string do not prove byte equality of the entire running backend container. The image was built outside Git and no runtime source-commit stamp exists; the audit records this provenance limitation rather than inventing a deployed Git SHA.

Actual downloaded ZIP CRC, contents and image hashes were checked. Six synthetic crop cases test geometry, not human benefit. Desktop and narrow mobile layout were inspected; physical touch hardware was not tested.

## Failures and limitations
An early version selected an inner printed rectangle. The retained safeguard and generated inner-table scenario demonstrate abstention and correction. Reused SmartDoc development frames showed v0.4 0/15, v0.5 15/15 and conservative v0.6 13/15 at IoU >=0.8, with two abstentions. These tuned-on frames do not establish independent current-release accuracy. Third-party frames are not distributed.

Weak edges, nested rectangles, missing content, multi-page scenes and severe blur remain difficult. No measured OCR improvement, time savings or adoption. Application code does not persist source images, but infrastructure must be reviewed separately before sensitive use. Remote processing uploads images; use fictional documents. Private access does not stop ECR/log storage costs or impose a hard budget cap.

## Reproduce and licenses
README supplies pinned installation and tests; DEPLOYMENT distinguishes IAM-only reproduction from the submitted authenticated gateway. Source MIT; OpenCV Apache-2.0 and NumPy BSD-3-Clause retain their notices in installed distributions. Generated fixtures are defined in vision.py and used by demo.py. AI coding assistance is disclosed, not claimed as an agentic runtime. The project and its public narrated video were submitted on 10 October; no judge acceptance or competition qualification is claimed.
