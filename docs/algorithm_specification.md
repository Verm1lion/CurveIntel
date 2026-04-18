# CurveIntel — Algorithm Specification

**Version:** 1.0.0
**Date:** 18 Nisan 2026
**Standard:** ISO 6892-1:2019 (Metallic materials — Tensile testing)

---

## 1. Elastic Modulus (E)

**ISO Reference:** Annex G (Determination of modulus of elasticity)
**Method:** Ordinary Least Squares (OLS) linear regression on elastic region

### Algorithm
1. Identify elastic region: stress in [0.05 * max_stress, 0.50 * max_stress]
2. Pre-filter: RANSAC regression to remove outliers (if R2 < threshold)
3. OLS fit: `stress = E * strain + intercept`
4. Quality gate: R2 >= 0.9990 (configurable, default strict)

### Parameters
| Parameter | Default | ISO Ref |
|---|---|---|
| Lower bound | 5% of max stress | Annex G |
| Upper bound | 50% of max stress | Annex G |
| R2 threshold | 0.9990 | NPL GPG 98 |
| RANSAC enabled | True | Supplementary |

### Libraries
- `numpy.polyfit` (degree=1)
- `sklearn.linear_model.RANSACRegressor`

### Known Limitations
- NPL GPG 98: typical u(E)/E = 1-2% (best), 4-14% (standard/worst)
- Toe compensation quality affects result significantly
- Pre-calculated stress-strain data may yield non-physical E values

---

## 2. Yield Strength (Rp0.2 / ReH / ReL)

**ISO Reference:** Clause 13.1, Annex A.3.2
**Method:** 0.2% offset + dual detection (continuous/discontinuous yield)

### Algorithm
1. Compute offset line: `stress = E * (strain - 0.002)`
2. Find intersection of offset line with stress-strain curve
3. If discontinuous yield detected (local max before offset):
   - ReH = local maximum stress
   - ReL = subsequent local minimum
4. Otherwise: Rp0.2 = offset intersection point

### ISO A.3.2 Two-Condition Test
- Condition 1: Force must reach local maximum before offset intersection
- Condition 2: Subsequent force must drop below maximum
- If both met: discontinuous yield (ReH/ReL behavior)

### Libraries
- `numpy.interp` for intersection
- `scipy.signal.savgol_filter` for smoothing

---

## 3. Ultimate Tensile Strength (Rm / UTS)

**ISO Reference:** Clause 13.2
**Method:** Maximum stress on Savitzky-Golay filtered curve

### Algorithm
1. Apply SG filter (window=21, polyorder=3) to stress data
2. Rm = max(filtered_stress)
3. Dual storage: also record unfiltered max for comparison

### Libraries
- `scipy.signal.savgol_filter`

---

## 4. Elongation at Break (At)

**ISO Reference:** Clause 20.1, Annex A.3.6.1
**Method:** Force-drop detection at fracture point

### Algorithm
1. Search backward from end of curve
2. Detect fracture: stress drop > 30% of Rm within 50 points
3. At = strain at fracture point * 100 (%)
4. Fallback: last data point if no clear fracture

---

## 5. Uniform Elongation (Ag)

**ISO Reference:** Clause 20.3
**Method:** Considere criterion (strain at UTS)

### Algorithm
1. Ag = strain at maximum stress point * 100 (%)

---

## 6. Strain Hardening Exponent (n)

**ISO Reference:** ISO 10275:2020
**Method:** Hollomon power law fit

### Algorithm
1. Identify fitting range: strain in [offset_strain + 0.01, strain_at_UTS]
2. Log-log fit: `log(stress) = n * log(strain) + log(K)`
3. n = slope of log-log regression

### Libraries
- `numpy.polyfit(log_strain, log_stress, 1)`

---

## 7. Toughness (Ut)

**Method:** Trapezoidal integration of stress-strain curve

### Algorithm
1. Ut = trapz(stress, strain) in MJ/m3

### Libraries
- `numpy.trapz`

---

## 8. Anomaly Detection

### 8.1 Grip Slippage
**Method:** Negative stress-derivative detection in elastic region

### 8.2 Sensor Saturation
**Method:** Constant-value plateau detection (>20 consecutive identical readings)

### 8.3 Noise Analysis
**Method:** SNR calculation on elastic region derivative

### 8.4 Curve Integrity
**Method:** Monotonicity and completeness checks

### 8.5 Property Validation
**Method:** Cross-property physical consistency (e.g., Rp0.2 < Rm)

---

## 9. Statistical QC (Batch)

### 9.1 Outlier Detection
| n | Method | Reference |
|---|---|---|
| 3-7 | Dixon Q10 | Dean & Dixon 1951, Rorabacher 1991 |
| >= 8 | Grubbs | ISO 5725-2:2019, Grubbs 1969 |

Max removals per batch: 1 (ASTM E178 masking prevention)

### 9.2 Confidence Interval
**Method:** t-distribution based 95% CI
`CI = mean +/- t(alpha/2, n-1) * std / sqrt(n)`

### 9.3 SPC
**Method:** Individuals + Moving Range chart (X-bar/R)
- Control limits: UCL/LCL = CL +/- 3*sigma_est
- Nelson 8 rules for pattern detection

---

## 10. Strain Rate Validation

**ISO Reference:** ISO 6892-1:2019 Table B.1
**Method:** Strain rate calculation from time-stamped data

### Algorithm
1. Compute strain rate: d(strain)/d(time)
2. Classify into ISO Range 1-4
3. Validate against Table B.1 limits

---

## Document Control

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-04-18 | CurveIntel | Initial release |
