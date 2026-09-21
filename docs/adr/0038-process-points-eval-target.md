# Process Points as optional backtest evaluation target

Model MAE / signed bias may score Gameweek Projection against **Process Points** (goals/assists from Official `expected_goals` / `expected_assists`; other components Realized) instead of **Realized Points**, to reduce finish luck on goals/assists. Default and ADR 0033 Champion Signed Bias gate stay Realized Points. CLI: `commands.backtest --eval_target process`. Not FPL `ep_*`. Not a calibration layer.
