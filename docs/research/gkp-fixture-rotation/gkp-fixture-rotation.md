# Starter Goalkeeper Fixture Rotation & FDR Correlation Study

**Updated**: 2026-08-03T04:48:00+07:00  
**Data stamp**: FPL API processed snapshot (2026-08-03)  
**Season**: 2026/27  
**Purpose**: Identify starter goalkeeper pairs costing <= £9.5m combined with the highest negative FDR correlation and lowest rotated average FDR to enable weekly fixture swapping.  
**Sources**: `data/processed/fixtures.parquet`, `data/processed/players.parquet`, `data/processed/clubs.parquet`  
**Artifact**: [`gkp_rotation_matrix.csv`](../../../data/research/gkp-fixture-rotation/gkp_rotation_matrix.csv)  
**Script**: [`run_gkp_rotation_analysis.py`](run_gkp_rotation_analysis.py)  

---

## Agent Prompt

Evaluate all starter goalkeeper pairs from different clubs with a total combined cost <= £9.5m. Compute weekly Fixture Difficulty Rating (FDR) Pearson correlations and rotated effective FDR values across multiple planning horizons (GW1–6, GW1–10, GW1–19, Full Season GW1–38). Present top complementary rotation pairs by budget tier.

---

## Method

1. **Goalkeeper Selection**: Extracted starting / primary goalkeepers for all 20 clubs from `players.parquet` filtered by position (GKP / `position_id = 1`) and priced between £4.0m and £5.5m.
2. **FDR Matrix Construction**: Built a Club × Gameweek matrix containing weekly defense FDR ratings (1 = easiest, 5 = hardest).
3. **Correlation & Rotation Metrics**:
   - **FDR Correlation ($r$)**: Pearson correlation coefficient between the two clubs' weekly FDR sequences. Strong negative correlation ($r < -0.30$) indicates when one keeper has a tough fixture, the other has an easy fixture.
   - **Rotated Average FDR**: Average of $\min(\text{FDR}_1, \text{FDR}_2)$ across all gameweeks in the horizon.
   - **FDR Gain**: Difference between the best single keeper's unrotated average FDR and the rotated pair's average FDR.
   - **Easy Gameweeks**: Number of gameweeks in which the rotated pair provides an FDR $\le 2$ fixture.

---

## Findings

### 1. Overall Top Rotation Pairs (Full Season GW1–38)

| GKP 1 (Club, Price) | GKP 2 (Club, Price) | Total Price | FDR Corr ($r$) | Rotated Avg FDR | FDR Gain | Easy GWs ($\le 2$) |
|---|---|---|---|---|---|---|
| **Steele** (BHA, £4.0m) | **Lammens** (MUN, £5.0m) | **£9.0m** | **-0.4170** | **2.5000** | +0.50 | 21 / 38 (55%) |
| **Sels** (NFO, £5.0m) | **Dubravka** (TOT, £4.0m) | **£9.0m** | **-0.3981** | **2.4737** | +0.58 | 20 / 38 (53%) |
| **Petrović** (BOU, £4.5m) | **Sels** (NFO, £5.0m) | **£9.5m** | **-0.3623** | **2.4737** | +0.58 | 20 / 38 (53%) |
| **Steele** (BHA, £4.0m) | **Roefs** (SUN, £5.0m) | **£9.0m** | **-0.3451** | **2.5263** | +0.55 | 20 / 38 (53%) |
| **Dubravka** (TOT, £4.0m) | **Roefs** (SUN, £5.0m) | **£9.0m** | **-0.3352** | **2.5000** | +0.55 | 20 / 38 (53%) |

---

### 2. Opening Horizon (GW1–10 Early Season Peak Correlation)

| Rank | Pair | Total Price | GW1-10 FDR Corr | Rotated Avg FDR | Easy GWs (FDR $\le 2$) |
|---|---|---|---|---|---|
| 1 | **Petrović** (BOU £4.5m) + **Sels** (NFO £5.0m) | **£9.5m** | **-0.7618** | **2.40** | 6 / 10 |
| 2 | **Palmer** (IPS £4.0m) + **Dubravka** (TOT £4.0m) | **£8.0m** | **-0.6704** | **2.50** | 5 / 10 |
| 3 | **Leno** (FUL £4.5m) + **Perri** (LEE £4.5m) | **£9.0m** | **-0.5976** | **2.50** | 5 / 10 |
| 4 | **Steele** (BHA £4.0m) + **Phillips** (HUL £4.0m) | **£8.0m** | **-0.5863** | **2.60** | 4 / 10 |
| 5 | **Sels** (NFO £5.0m) + **Dubravka** (TOT £4.0m) | **£9.0m** | **-0.5710** | **2.50** | 5 / 10 |

---

### 3. Top Pairings by Budget Tier

#### **Tier A: Premium Budget (£9.5m = £5.0m + £4.5m or £5.5m + £4.0m)**
- **Petrović (BOU £4.5m) + Sels (NFO £5.0m)**: Best overall opening rotation. FDR correlation **-0.7618** (GW1-10) and **-0.8216** (GW1-6). Gives an FDR $\le 2$ fixture in 6 of first 10 gameweeks.
- **Pickford (EVE £5.5m) + Dubravka (TOT £4.0m)**: Premium £5.5m keeper paired with £4.0m starter. Rotated average FDR of **2.47** over GW1-19.

#### **Tier B: Classic Budget Pair (£9.0m = £4.5m + £4.5m or £5.0m + £4.0m)**
- **Sels (NFO £5.0m) + Dubravka (TOT £4.0m)**: Most consistent long-term pair ($r = -0.3981$ full season, $r = -0.5710$ GW1-10). Gives rotated FDR of **2.47** over 38 weeks.
- **Lammens (MUN £5.0m) + Steele (BHA £4.0m)**: Highest negative full-season correlation (**-0.4170**). 21 easy fixtures (55% of season).
- **Leno (FUL £4.5m) + Perri (LEE £4.5m)**: Extreme early negative correlation (**-0.8305** GW1-6, **-0.5976** GW1-10).

#### **Tier C: Ultra-Budget (£8.0m–£8.5m)**
- **Palmer (IPS £4.0m) + Dubravka (TOT £4.0m)** (£8.0m): Strong negative correlation (**-0.6704** GW1-10) for minimum price.
- **Steele (BHA £4.0m) + Phillips (HUL £4.0m)** (£8.0m): Early negative correlation (**-0.5863** GW1-10).
- **Leno (FUL £4.5m) + Dubravka (TOT £4.0m)** (£8.5m): Rotated FDR **2.47** over GW1-19.

---

## Decision & Practical Recommendation

1. **If allocating £9.5m**: Select **Petrović (£4.5m, BOU)** + **Sels (£5.0m, NFO)**. Outstanding complementarity in GW1–10.
2. **If allocating £9.0m**: Select **Sels (£5.0m, NFO)** + **Dubravka (£4.0m, TOT)** or **Steele (£4.0m, BHA)** + **Lammens (£5.0m, MUN)**.
3. **If allocating £8.0m**: Select **Dubravka (£4.0m, TOT)** + **Palmer (£4.0m, IPS)**.

---

## Risks and Unknowns

- **Rotation / Place Security**: £4.0m/£4.5m keepers like Steele/Verbruggen or Dubravka/Kinsky may be subject to cup/league manager rotation. Monitor starting line-ups in pre-season.
- **Double Gameweeks**: Double gameweeks later in the season can alter single-game FDR priority.
