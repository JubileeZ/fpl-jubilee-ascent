import pandas as pd
from pathlib import Path

def refresh_expected_roles(
    input_csv: str = "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv",
    output_csvs: list[str] = None
):
    if output_csvs is None:
        output_csvs = [
            "data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv"
        ]

    df = pd.read_csv(input_csv)

    # 1. Antonin Kinsky (Spurs GK) -> Nailed Starter
    kinsky_mask = (df["club_short"] == "TOT") & (df["web_name"].str.contains("Kinsky", case=False, na=False))
    if kinsky_mask.any():
        df.loc[kinsky_mask, "expected_role"] = "Nailed Starter"
        df.loc[kinsky_mask, "p_start"] = 0.90
        df.loc[kinsky_mask, "p_sub_in"] = 0.05
        df.loc[kinsky_mask, "p_dnp"] = 0.05
        df.loc[kinsky_mask, "confidence"] = "high"
        df.loc[kinsky_mask, "draft_availability"] = "eligible"
        df.loc[kinsky_mask, "reason"] = "De Zerbi officially confirmed Kinsky as Spurs #1 keeper for 2026/27."

    # 2. James Trafford (Leeds GK) -> Nailed Starter
    trafford_mask = (df["web_name"].str.contains("Trafford", case=False, na=False))
    if trafford_mask.any():
        df.loc[trafford_mask, "club"] = "Leeds United"
        df.loc[trafford_mask, "club_short"] = "LEE"
        df.loc[trafford_mask, "expected_role"] = "Nailed Starter"
        df.loc[trafford_mask, "p_start"] = 0.90
        df.loc[trafford_mask, "draft_availability"] = "eligible"
        df.loc[trafford_mask, "reason"] = "Completed £40m record transfer to Leeds as starting GK."

    # 3. Carl Rushworth (Coventry GK) -> Nailed Starter
    rushworth_mask = (df["web_name"].str.contains("Rushworth", case=False, na=False))
    if rushworth_mask.any():
        df.loc[rushworth_mask, "club"] = "Coventry City"
        df.loc[rushworth_mask, "club_short"] = "COV"
        df.loc[rushworth_mask, "expected_role"] = "Nailed Starter"
        df.loc[rushworth_mask, "p_start"] = 0.90
        df.loc[rushworth_mask, "draft_availability"] = "eligible"
        df.loc[rushworth_mask, "reason"] = "Signed £22m from Brighton to start following Dovin ACL tear."

    # 4. Konstantinos Tzolakis (Hull GK) -> Nailed Starter
    tzolakis_mask = (df["web_name"].str.contains("Tzolakis", case=False, na=False))
    if tzolakis_mask.any():
        df.loc[tzolakis_mask, "club"] = "Hull City"
        df.loc[tzolakis_mask, "club_short"] = "HUL"
        df.loc[tzolakis_mask, "expected_role"] = "Nailed Starter"
        df.loc[tzolakis_mask, "p_start"] = 0.90
        df.loc[tzolakis_mask, "draft_availability"] = "eligible"
        df.loc[tzolakis_mask, "reason"] = "Signed £20m from Olympiacos as primary starter."

    # 5. Sandro Tonali (Spurs MID) -> Nailed Starter
    tonali_mask = (df["web_name"].str.contains("Tonali", case=False, na=False))
    if tonali_mask.any():
        df.loc[tonali_mask, "club"] = "Tottenham Hotspur"
        df.loc[tonali_mask, "club_short"] = "TOT"
        df.loc[tonali_mask, "expected_role"] = "Nailed Starter"
        df.loc[tonali_mask, "p_start"] = 0.90
        df.loc[tonali_mask, "draft_availability"] = "eligible"
        df.loc[tonali_mask, "reason"] = "Confirmed £100m transfer from Newcastle to Spurs."

    # 6. Maxence Lacroix (Chelsea DEF) -> Nailed Starter
    lacroix_mask = (df["web_name"].str.contains("Lacroix", case=False, na=False))
    if lacroix_mask.any():
        df.loc[lacroix_mask, "club"] = "Chelsea"
        df.loc[lacroix_mask, "club_short"] = "CHE"
        df.loc[lacroix_mask, "expected_role"] = "Nailed Starter"
        df.loc[lacroix_mask, "p_start"] = 0.90
        df.loc[lacroix_mask, "draft_availability"] = "eligible"
        df.loc[lacroix_mask, "reason"] = "Confirmed £52m transfer from Crystal Palace to Chelsea."

    # 7. Bruno Guimarães (Arsenal MID) -> Nailed Starter
    bruno_mask = (df["web_name"] == "Bruno G.")
    if bruno_mask.any():
        df.loc[bruno_mask, "club"] = "Arsenal"
        df.loc[bruno_mask, "club_short"] = "ARS"
        df.loc[bruno_mask, "expected_role"] = "Nailed Starter"
        df.loc[bruno_mask, "p_start"] = 0.90
        df.loc[bruno_mask, "draft_availability"] = "eligible"
        df.loc[bruno_mask, "reason"] = "Confirmed £75m transfer from Newcastle to Arsenal as starting CM."

    # 8. Danny Welbeck (Chelsea FWD) -> Rotation
    welbeck_mask = (df["web_name"] == "Welbeck")
    if welbeck_mask.any():
        df.loc[welbeck_mask, "club"] = "Chelsea"
        df.loc[welbeck_mask, "club_short"] = "CHE"
        df.loc[welbeck_mask, "expected_role"] = "Rotation"
        df.loc[welbeck_mask, "p_start"] = 0.35
        df.loc[welbeck_mask, "draft_availability"] = "not_role_eligible"
        df.loc[welbeck_mask, "reason"] = "Confirmed £5m transfer from Brighton to Chelsea as forward depth."

    # Save to target paths
    for out_path in output_csvs:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False)
        print(f"Updated {p} ({len(df)} rows)")

    return df

if __name__ == "__main__":
    refresh_expected_roles()
