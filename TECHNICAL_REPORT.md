# CaptureGate technical report — v0.10

## Problem and implementation
People handing document photographs into another workflow need useful framing, retake advice and control when automatic cropping fails. No medical, employment, identity or legal decisions are made. Benefit and willingness to pay remain unmeasured.

Pinned OpenCV 5.0.0.93 and NumPy 2.3.5 run in Python. vision.py resizes/smooths images, applies several Canny thresholds, morphological closing and convex quadrilateral filtering. Candidate sides require lighter-paper support. Laplacian detail and bright-region signals are measured inside a candidate. Unsupported boundaries abstain. rectify.py and page_crop.py support perspective warping; recovery.py provides natural, LAB-luminance contrast and adaptive black-and-white output, bounded to a 1200-pixel long side without upsampling. Manual geometry uses original pixels and is validated. Gentle sharpening changes contrast, not missing detail.

## Human review
Original findings remain separate from proposals. Crop-loss shading shows excluded regions. Changes invalidate acceptance; asynchronous export checks prevent stale approval reuse. A ZIP binds the actual reviewed JPEG bytes to JSON through SHA-256 and includes readable warnings. Hashing detects mismatch; it is not an authenticity signature. Manual approval never certifies whole-page completeness.

## AWS and evidence
The shared service and UI run in an x86_64 Lambda container stored in ECR. infra.json specifies AWS_IAM, 1024 MB, a 15-second timeout and three-day logs. No public endpoint is claimed. Organizer screen-share scheduling remains pending.

On 8 October 2026: 67 Linux Python tests and seven generated Lambda checks passed; 46 controller tests passed locally. Deployed app.js SHA-256 matches source: `011d00c775437d88f69323ccd32b3859e5f932eb8b144f08c8a73349047d0df6`. Image digest: `sha256:e7c7ce3f7f3f3b51210035e2299ca56edf72b0b8becfef1b5548883419b1067b`. Backend policy remains capturegate-v0.9-manual-borders; v0.10 improves handoff, not independently validated detector accuracy. Optional public_guard.py is tested but not configured in the private pilot.

Actual downloaded ZIP CRC, contents and image hashes were checked. Six synthetic crop cases test geometry, not human benefit. Desktop and narrow mobile layout were inspected; physical touch hardware was not tested.

## Failures and limitations
An early version selected an inner printed rectangle. The retained safeguard and generated inner-table scenario demonstrate abstention and correction. Reused SmartDoc development frames showed v0.4 0/15, v0.5 15/15 and conservative v0.6 13/15 at IoU >=0.8, with two abstentions. These tuned-on frames do not establish independent current-release accuracy. Third-party frames are not distributed.

Weak edges, nested rectangles, missing content, multi-page scenes and severe blur remain difficult. No measured OCR improvement, time savings or adoption. Application code does not persist source images, but infrastructure must be reviewed separately before sensitive use. Remote processing uploads images; use fictional documents. Private access does not stop ECR/log storage costs or impose a hard budget cap.

## Reproduce and licenses
README supplies pinned installation and tests; DEPLOYMENT describes private reproduction. Source MIT; OpenCV Apache-2.0 and NumPy BSD-3-Clause retain their notices in installed distributions. Generated examples originate in demo.py. AI coding assistance is disclosed, not claimed as an agentic runtime.
