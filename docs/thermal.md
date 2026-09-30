# Thermal design

Derived from `params.yaml`. **Every figure here is analytical and unverified.**
The stage-4 bench measurement (SPECIFICATION §9.1) is what makes them real.

---

## 1. What has to be got rid of

At the 690W design point:

```
buck stage losses = 690 / 0.95 − 690 ≈ 36W
control + display                    ≈  2W
                                     ------
total inside the chassis             ≈ 38W
```

**The PSU's own ~72W of loss is not in this budget.** The RSP-1000-48 has its own
fan and exhausts its own heat through its own airflow path. Do not obstruct it,
and do not count it twice.

> **This is why the fanless UHP-750-48 was rejected** (`power-budget.md` §3).
> A conduction-cooled unit has no such path: its ~38W conducts into whatever it is
> bolted to, which is the chassis, roughly **doubling** the 38W budget above and
> the 4.5 CFM requirement below. On a first build where the thermal design is
> calculated rather than measured, doubling the load on the one thing you have not
> verified is a bad trade for 3% efficiency.

## 2. Airflow required

For a 15°C rise across the chassis:

```
V = P / (ρ · c_p · ΔT)
  = 38 / (1.2 × 1005 × 15)
  = 2.1 L/s
  ≈ 4.5 CFM
```

**3 × Noctua NF-A4x20 PWM**, ~9.4 CFM free air each. Even heavily derated for
static pressure through a populated 1U chassis this is several times the
requirement.

**Three fans are specified for distribution and tolerance, not capacity.** One
would move enough air; three put a fan over each 2-channel board, and mean a
single fan failure (T-5) degrades rather than disables cooling.

## 3. Where the heat actually is

Per channel at 7A, from the loss model:

| Loss | Value | Where it lands |
|---|---|---|
| **High-side FET switching** | **1.68W** | **One SO-8 package — the hot spot** |
| Inductor DCR | 0.71W | XAL1510-223 body |
| Current sense resistor (7mΩ) | 0.34W | 2512, needs a 1W part |
| Low-side FET conduction | 0.23W | SO-8 |
| Inductor core | ~0.20W | XAL1510 body |
| High-side FET conduction | 0.16W | SO-8 |
| Gate drive | 0.11W | Controller |
| Telemetry shunt (2mΩ) | 0.10W | 2512 |
| Caps ESR, I_q, copper | ~0.4W | Distributed |
| **Modelled total** | **~3.9W** | → 97.1% |
| **Design target** | **≤6.6W** | **95%** |

**Switching loss dominates, and that is a consequence of the 48V input.**
`0.5 × V_in × I_out × (t_r + t_f) × f_sw` scales directly with input voltage, so
a 48V bus pays roughly twice what a 24V bus would for the same output. This
drives three decisions:

- **250kHz, not 300kHz+.** Switching loss is linear in frequency. The cost is a
  physically larger inductor, which 1U can accommodate (10mm tall in a 40mm
  budget).
- **Low gate charge is a primary FET selection criterion**, ahead of the
  headline R_ds(on) figure that usually gets quoted.
- It is the single strongest argument that was made for an integrated-FET
  regulator — and the reason that route was investigated properly before being
  rejected. See §4 below.

**Design efficiency is held at 95%, not the 97.1% the model gives**, because the
model omits layout-dependent losses entirely: copper resistance, parasitic
inductance in the switching loop, and body-diode conduction during dead time.
Those are exactly the losses a first-time high-current layout gets wrong.

## 4. Why the heat had to be spread across discrete parts

The integrated-FET route (LT8645S) would have cut layout risk substantially,
which mattered given the decision on R-0. **It fails on package thermals**, and
the numbers are worth keeping visible:

θ_JA = 31°C/W, θ_JC(pad) = 6°C/W, T_J(max) = 125°C.

| Assumed efficiency | P_diss | T_J at 35°C ambient |
|---|---|---|
| 95% | 7.0W | **252°C** |
| 96% | 5.5W | **207°C** |
| 96%, generous θ_JA = 15°C/W | 5.5W | **118°C — no margin** |

Even the most favourable case sits on the limit, and requires assuming best-case
efficiency *and* half the datasheet θ_JA simultaneously.

**The 8A rating is real, but it is a rating at low output *power*.** At 5V/8A the
part delivers 40W and dissipates ~3W. Here it would deliver 133W. Conduction loss
scales with I² regardless of V_out, and all of it lands in one 4 × 7mm package.

**The discrete route wins precisely because it is discrete.** Two SO-8 FETs each
carry their own losses into their own thermal pad, with the inductor's ~0.9W in a
third package. The worst single component is the high-side FET at ~1.84W; at a
pour-assisted θ_JA of ~35°C/W that is a 64°C rise, so **T_J ≈ 99°C at 35°C
ambient with forced air still to come.** Spreading the heat is not a side benefit
here — it is the requirement.

## 5. Fan control

- **NTC per board** drives the curve (T-4). Quiet at idle, adequate under load.
- **Tach feedback per fan** (T-5). A silent fan failure precedes a thermal
  failure; it must be reported, not discovered.
- **Automatic thermal shutdown** as last-resort protection (P-10).

At cluster idle (78–180W output) chassis dissipation is under 10W and the fans
sit near minimum, which is how T-3's ≤35 dBA target is met. **The acoustic target
only has to be met at idle** — under sustained six-node load the rack is not
quiet regardless of what this box does.

## 6. Derating

**No component above 80% of its rated maximum** (T-2), at 35°C ambient (T-1).
35°C is a realistic rack inlet temperature, not a datasheet-friendly 25°C.

Verified at stage 4 with a 30-minute soak at 7A and an IR camera on the FETs, the
inductor and the sense resistor — and again after the 72-hour burn-in, because a
thermally-aged board is the one that matters.
