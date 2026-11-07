# Forecasting methodology

## Objective

The forecasting workflow estimates daily demand for each product using only observed transaction history from the UCI Online Retail II dataset. The system is designed to avoid leakage by using chronology-preserving splits and by keeping future information completely out of the training features.

## Data provenance and scope

- Observed demand comes from the raw transaction records after cleaning.
- Synthetic product costs, inventory snapshots, and supplier data are not used as ground-truth sales signals.
- We do not fabricate future actual sales. Forecast output includes `actual_demand = null` because the future demand is unobserved.

## Time-series validation design

For each product, the model selection stage follows these rules:

1. Convert the product-level demand history to a daily series with zero-filled missing dates.
2. Require a minimum of 90 days of valid history before training or evaluation.
3. Use chronological validation windows, not random train/test splitting.
4. Evaluate on multiple validation windows (14, 21, and 28 days when the data allows) to reduce dependence on a single horizon.
5. Reserve a final untouched test window after the model is chosen.
6. Compare all candidate models against baseline models before selecting the final model.

This protects the evaluation from data leakage and mirrors business forecasting practices where future demand is predicted from past observed demand only.

## Candidate models

Baseline models:

- Naive: last observed daily demand
- Moving Average: trailing 7-day average
- Seasonal Naive: same day-of-week value from the most recent matching seasonal pattern

Machine-learning models:

- Random Forest regressor using lag and rolling-demand features
- Gradient Boosting regressor using the same lagged feature set

The feature set includes lagged demand, 7-day and 28-day rolling averages, day-of-week, day-of-month, week-of-year, and month.

## Forecast metrics

The model selection step evaluates each candidate using the following metrics on the validation windows:

- MAE: mean absolute error
- RMSE: root mean squared error
- WAPE: weighted absolute percentage error, defined as sum(|actual - forecast|) / sum(|actual|) × 100
- sMAPE: symmetric mean absolute percentage error, with zero-denominator handling for exact-zero demand periods
- MAPE: mean absolute percentage error only on positive actual observations

### Zero-demand handling

- MAPE is computed only on days where `actual > 0`.
- If all actual observations in the evaluation window are zero, the MAPE is treated as undefined rather than forced to zero.
- WAPE is used to retain a percentage-based metric even when actual volumes are near zero but not entirely zero.
- sMAPE is computed with a zero-safe denominator; exact-zero pairs do not artificially produce a perfect score.

## Model selection and final evaluation

The candidate model with the lowest average validation MAE is selected using validation data only. The selected model is then re-evaluated on a final untouched test window that is not used in earlier validation decisions.

This ensures that the final reported performance is an honest estimate of predictive capability, not only a training fit.

## Limitations

- Intermittent demand can make percentage-based metrics unstable because zero-demand periods produce undefined or inflated ratios.
- Weekly seasonality is captured using a simple day-of-week seasonal baseline, but the project does not assume every product has a stable repeatable seasonal pattern.
- A model can still be selected even if it only marginally improves over the baseline. The methodology does not claim superiority without evidence from validation and final test metrics.
- Forecasts are for demand planning only; they are not observed business outcomes and are not substituted for actual inventory transactions.

## Output contract

Each forecast record includes:

- product ID
- forecast date
- predicted units
- selected model
- relative evaluation metrics
- validation period used for final evaluation
- a model limitation note

Predicted demand is constrained to be non-negative, and all future actual sales remain null because they are not observed data.
