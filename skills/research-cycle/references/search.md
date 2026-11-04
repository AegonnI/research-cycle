# Bounded architecture and model search

## Method scope

Contract: allowed families/architectures, custom networks, pretrained weights, data,
preprocessing, search algorithms, parameter ranges, resource ceilings and code-edit
boundaries. Unspecified methods are not automatically permitted. Separate fixed
benchmark conditions from optimization variables. A manifest is inventory, not install permission.

The ledger checks *declared* scientific fields through `method_scope`, for example:

```json
{
  "required_fields": ["family", "architecture", "seed", "fidelity", "code_sha256", "split_sha256"],
  "allowed_values": {"family": ["residual_cnn", "mobile_cnn", "custom_cnn"], "pretrained": [false]},
  "forbidden_values": {"architecture": ["vit_b_16"]},
  "numeric_bounds": {"parameters": {"min": 1000, "max": 30000000}, "image_size": {"min": 128, "max": 224}}
}
```

This does not inspect code behavior. An independent evaluator/OS permissions are
needed to enforce held-out access restrictions.

## Allocation and selection

Coverage quotas and fixed stage/reserve allocations apply only if the user requests
them. A target+wall task may focus early on promising candidates. Calibrate timeouts
from observed cost; do not exclude a family merely because its process deadline was too short.


1. Catalogue structural families before selecting favorites. Consider capacity,
   initialization, optimization and throughput as alternative explanations. An LR
   or seed change is not a new architecture. For custom CNNs record blocks/graph,
   depth, width, kernels, stride, skip connections, normalization and parameter count.
2. Measure pilot cost and size stages from remaining compute, preserving confirmation
   reserves. Contractual coverage minima remain requirements: report infeasibility,
   do not quietly lower them.
3. Use bounded screen/promote/confirm, such as successive halving, random, Bayesian or
   evolutionary search if permitted. Batch predictable work in a reusable controller;
   register/reserve each child trial before launch, even if the controller crashes.
4. Allocate explicitly to diversity and late-blooming/slower families. Random and
   pretrained initialization form separate strata unless initialization is a search
   variable. Equal epochs address comparable training; equal time addresses quality
   under compute constraints. Report actual time as well as training fidelity.
5. Early rankings are provisional. Save epochs, updates, sample counts, size, precision,
   elapsed time and prune reason. A shape test/catalogue entry is not a trained model.
   Training subsets preserve grouping; validation remains the contracted population.
6. Promote on validation alone under a prospective rule. Confirm using equal prescribed
   fidelity and fresh seeds; include a simple baseline. Report failures, prunes,
   best-so-far trajectory, coverage and uncertainty. Seed variation measures training
   instability, not uncertainty from sampling independent patients/datasets.
7. Aggregate/cluster-bootstrap at the independent unit. A slice-level primary score
   can be valid, but correlated slices are not independent patients. Many validation
   trials inflate winner optimism; held-out evaluation stays outside adaptive search.

Do not promise exhaustive NAS. Report catalogue size, actual training coverage,
promotion counts and untested options. Preserve negative results.
