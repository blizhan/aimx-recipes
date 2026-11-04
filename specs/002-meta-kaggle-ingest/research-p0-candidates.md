# P0 Heuristic v0 — Candidate Tables For Curator Review

**Date**: 2026-11-03 | **Snapshot**: Meta Kaggle 2026-11-01 (local) | **Research**: [research.md §R6](research.md#r6-p0-heuristic-candidate-proposal-only)

A planning worker produced these tables with the v0 heuristic during research. They contain identifiers, metrics, and counts only, and no source text.

They are **not** the reviewed list and decide nothing (C-16). The implemented heuristic regenerates them on each run as the candidate report. A curator records decisions in the reviewed list.

The "curator hint" column is the worker's manual reading of titles and signals. It is not part of the deterministic rule.

Signals: S1 tabular metric family · S2 tabular-file mention without media files · S3 no media indicators ·
S4 positive tag and no negative tag · S5 hard exclude. Curator hints are my manual reading of title, subtitle and signals. They are **not**
part of the deterministic rule.

### A. Proposed candidates (deterministic rule: not S5 ∧ S1 ∧ S3 ∧ (S2 ∨ S4))

| slug | year | class | metric | writeups | signals | review flags / curator hint |
|---|---|---|---|---|---|---|
| equity-post-HCT-survival-predictions | 2025 | other_tags | eefs_concordance_index (#70384193) | 32 | S1 S2 S3 S4 |  |
| neurips-open-polymer-prediction-2025 | 2025 | other_tags | open_polymer_2025 (#84603218) | 29 | S1 S2 S3 | bioseq; review: SMILES/molecular |
| otto-recommender-system | 2023 | other_tags | WeightedRecall@{K} | 27 | S1 S2 S3 S4 |  |
| liverpool-ion-switching | 2020 | other_tags | FScoreMacro | 25 | S1 S2 S3 | review: 1-D signal time series |
| nfl-big-data-bowl-2020 | 2020 | other_tags | CRPS | 25 | S1 S2 S3 S4 |  |
| stanford-covid-vaccine | 2020 | other_tags | MWCRMSE | 25 | S1 S2 S3 S4 | bioseq; review: RNA sequence data, not tabular |
| stanford-ribonanza-rna-folding | 2023 | other_tags | Mean Absolute Error (#39243586) | 25 | S1 S2 S3 S4 | bioseq; review: RNA sequence |
| data-science-bowl-2019 | 2020 | other_tags | QuadraticWeightedKappa | 24 | S1 S2 S3 |  |
| h-and-m-personalized-fashion-recommendations | 2022 | other_tags | MAP@{K} | 23 | S1 S2 S3 S4 |  |
| talkingdata-adtracking-fraud-detection | 2018 | untagged | AUC | 20 | S1 S2 S3 |  |
| um-game-playing-strength-of-mcts-variants | 2024 | other_tags | Mean Squared Error (#39243534) | 19 | S1 S2 S3 S4 |  |
| march-machine-learning-mania-2026 | 2026 | other_tags | MSE | 18 | S1 S2 S3 S4 |  |
| santander-value-prediction-challenge | 2018 | other_tags | RMSLE | 15 | S1 S2 S3 S4 |  |
| basket-analysis | 2017 | other_tags | FScoreMicro | 14 | S1 S3 S4 | thin_dataset_desc |
| microsoft-malware-prediction | 2019 | untagged | AUC | 13 | S1 S2 S3 |  |
| mitsui-commodity-prediction-challenge | 2026 | other_tags | MITSUI&CO. Commodity Prediction Metric (#87233352) | 13 | S1 S2 S3 S4 |  |
| widsdatathon2020 | 2020 | untagged | AUC | 13 | S1 S2 S3 |  |
| leap-atmospheric-physics-ai-climsim | 2024 | other_tags | R2 Score (#39243596) | 12 | S1 S2 S3 S4 | review: simulator emulation (tabular arrays) |
| mercari-price-suggestion-challenge | 2018 | untagged | RMSLE | 12 | S1 S2 S3 |  |
| WiDSWorldWide_GlobalDathon26 | 2026 | untagged | wildfire_time_to_hit_metric (#107559884) | 12 | S1 S2 S3 |  |
| recruit-restaurant-visitor-forecasting | 2018 | untagged | RMSLE | 11 | S1 S2 S3 |  |
| widsdatathon2021 | 2021 | untagged | AUC | 11 | S1 S2 S3 |  |
| ncaam-march-mania-2021 | 2021 | other_tags | LogLoss | 10 | S1 S2 S3 S4 |  |
| nfl-big-data-bowl-2026-prediction | 2026 | other_tags | NFL_2025 (#92925683) | 10 | S1 S2 S3 S4 | review: tracking-data trajectories |
| actuarial-loss-estimation | 2021 | untagged | RMSE | 9 | S1 S2 S3 |  |
| march-machine-learning-mania-2023 | 2023 | other_tags | MSE | 9 | S1 S2 S3 S4 |  |
| march-machine-learning-mania-2024 | 2024 | other_tags | March Mania 2024 Metric (#51183962) | 9 | S1 S2 S3 S4 |  |
| march-machine-learning-mania-2025 | 2025 | other_tags | MSE | 9 | S1 S2 S3 S4 |  |
| mlb-player-digital-engagement-forecasting | 2021 | untagged | MeanColumnwiseMAE | 9 | S1 S2 S3 |  |
| novozymes-enzyme-stability-prediction | 2023 | other_tags | SpearmanR | 9 | S1 S2 S3 | bioseq; review: protein sequence |
| mens-march-mania-2022 | 2022 | other_tags | LogLoss | 8 | S1 S2 S3 S4 |  |
| widsdatathon2023 | 2023 | untagged | RMSE | 8 | S1 S2 S3 |  |
| womens-machine-learning-competition-2019 | 2019 | other_tags | LogLoss | 8 | S1 S2 S3 S4 |  |
| womens-march-mania-2022 | 2022 | other_tags | LogLoss | 8 | S1 S2 S3 S4 |  |
| afsis-soil-properties | 2014 | untagged | MCRMSE | 6 | S1 S2 S3 |  |
| widsdatathon2024-challenge1 | 2024 | untagged | Roc Auc Score (#39244492) | 6 | S1 S2 S3 |  |
| chess | 2010 | untagged | RMSE | 5 | S1 S2 S3 |  |
| cl-cv2020 | 2020 | untagged | FScoreMicro | 5 | S1 S2 S3 | likely FP: movie-poster images |
| kdd-cup-2013-author-disambiguation | 2013 | untagged | FScoreMicro | 5 | S1 S2 S3 | review: relational/entity resolution |
| mens-machine-learning-competition-2019 | 2019 | other_tags | LogLoss | 5 | S1 S2 S3 S4 |  |
| nomad2018-predict-transparent-conductors | 2018 | other_tags | MCRMSLE | 5 | S1 S2 S3 |  |
| 2019-3rd-ml-month-with-kakr | 2019 | untagged | FScoreMicro | 4 | S1 S2 S3 | non_english; likely FP: car image classification (Korean subtitle evades keywords) |
| autism-prediction | 2022 | untagged | AUC | 4 | S1 S2 S3 |  |
| higgs-boson | 2014 | untagged | HiggsBosonApproximateMedianSignificance | 4 | S1 S2 S3 |  |
| liberty-mutual-group-property-inspection-prediction | 2015 | other_tags | NormalizedGini | 4 | S1 S2 S3 S4 |  |
| ncaaw-march-mania-2021 | 2021 | other_tags | LogLoss | 4 | S1 S2 S3 S4 |  |
| netflix-appetency | 2022 | untagged | AUC | 4 | S1 S2 S3 |  |
| nta-landmarks-detection | 2020 | untagged | MSE | 4 | S1 S2 S3 | thin_dataset_desc; likely FP: facial keypoints from images |
| products-10k | 2020 | untagged | CategorizationAccuracy | 4 | S1 S2 S3 | likely FP: product image recognition (img kw 5 < threshold) |
| amazon-employee-access-challenge | 2013 | untagged | AUC | 3 | S1 S2 S3 |  |
| challenges-in-representation-learning-the-black-box-learning-challenge | 2013 | untagged | CategorizationAccuracy | 3 | S1 S2 S3 |  |
| criteo-display-ad-challenge | 2014 | untagged | LogLoss | 3 | S1 S2 S3 |  |
| dmia-surnames-classification | 2018 | untagged | AUC | 3 | S1 S2 S3 | non_english |
| FacebookRecruiting | 2012 | untagged | MAP@k | 3 | S1 S2 S3 | review: graph link prediction |
| kkbox-music-recommendation-challenge | 2017 | untagged | AUC | 3 | S1 S2 S3 |  |
| two-sigma-financial-modeling | 2017 | other_tags | RValue | 3 | S1 S2 S3 S4 |  |
| 2019-1st-ml-month-with-kakr | 2019 | untagged | CategorizationAccuracy | 2 | S1 S2 S3 | non_english |
| acm-sf-chapter-hackathon-big | 2012 | untagged | MAP@k | 2 | S1 S2 S3 |  |
| cat-in-the-dat-ii | 2020 | other_tags | AUC | 2 | S1 S2 S3 S4 |  |
| dig-4-bio-raman-transfer-learning-challenge | 2025 | untagged | R2 Score (#39243596) | 2 | S1 S2 S3 | review: spectra |
| porto-seguro-data-challenge | 2021 | untagged | F_{Beta} (deprecated) | 2 | S1 S2 S3 |  |
| predict-potential-spammers-on-fiverr | 2022 | untagged | FScoreMacro | 2 | S1 S2 S3 |  |
| reducing-commercial-aviation-fatalities | 2019 | untagged | MulticlassLoss | 2 | S1 S2 S3 | signal |
| socialNetwork | 2011 | untagged | AUC | 2 | S1 S2 S3 | review: graph link prediction |
| sugiura-lab-first-competition | 2021 | untagged | CategorizationAccuracy | 2 | S1 S2 S3 | review: thin description |
| ubaar-competition | 2018 | untagged | MAPE | 2 | S1 S2 S3 |  |
| zillow-prize-1 | 2018 | other_tags | ZillowMAE | 2 | S1 S2 S3 S4 |  |
| 2020-ai-termproject-18011793 | 2020 | untagged | RMSE | 1 | S1 S2 S3 | non_english |
| accelerometer-biometric-competition | 2013 | untagged | AUC | 1 | S1 S2 S3 |  |
| acm-sf-chapter-hackathon-small | 2012 | untagged | MAP@k | 1 | S1 S2 S3 |  |
| acquire-valued-shoppers-challenge | 2014 | untagged | AUC | 1 | S1 S2 S3 |  |
| aiseaweather | 2020 | untagged | RMSE | 1 | S1 S2 S3 | non_english |
| ams-2014-solar-energy-prediction-contest | 2013 | untagged | MAE | 1 | S1 S2 S3 |  |
| avazu-ctr-prediction | 2015 | untagged | LogLoss | 1 | S1 S2 S3 |  |
| banco-galicia-dataton-2019 | 2019 | untagged | AUC | 1 | S1 S2 S3 |  |
| battlefin-s-big-data-combine-forecasting-challenge | 2013 | untagged | MAE | 1 | S1 S2 S3 |  |
| beyond-analysis | 2021 | untagged | MCRMSE | 1 | S1 S2 S3 |  |
| bluebook-for-bulldozers | 2013 | untagged | RMSLE | 1 | S1 S2 S3 |  |
| classification-data-challenge | 2023 | untagged | AUC | 1 | S1 S2 S3 |  |
| coffeecsmr | 2021 | untagged | RMSE | 1 | S1 S2 S3 | non_english |
| DATACUP-ROUND2 | 2021 | untagged | RMSE | 1 | S1 S2 S3 |  |
| energy-anomaly-detection | 2022 | untagged | AUC | 1 | S1 S2 S3 |  |
| event-recommendation-engine-challenge | 2013 | untagged | MAP@k | 1 | S1 S2 S3 |  |
| gmsc-thebridge-dsft2109 | 2021 | untagged | AUC | 1 | S1 S2 S3 | thin_dataset_desc |
| hhp | 2013 | untagged | RMSLE | 1 | S1 S2 S3 |  |
| kaggledatafest | 2021 | untagged | FScoreMicro | 1 | S1 S2 S3 |  |
| kdd-cup-2013-author-paper-identification-challenge | 2013 | untagged | MAP@{K}_OLD | 1 | S1 S2 S3 | review: relational |
| kkbox-churn-prediction-challenge | 2017 | other_tags | LogLoss | 1 | S1 S2 S3 S4 |  |
| mf-accelerator | 2020 | untagged | FScoreMacro | 1 | S1 S2 S3 | non_english |
| ncaaw-march-mania-2021-spread | 2021 | other_tags | RMSE | 1 | S1 S2 S3 S4 |  |
| nytfug | 2022 | untagged | CategorizationAccuracy | 1 | S1 S2 S3 |  |
| pf2012-diabetes | 2012 | untagged | LogLoss | 1 | S1 S2 S3 |  |
| predict-closed-questions-on-stack-overflow | 2012 | untagged | MulticlassLossOld | 1 | S1 S2 S3 | likely FP: text classification |
| predict-impact-of-air-quality-on-death-rates | 2017 | untagged | RMSE | 1 | S1 S2 S3 |  |
| qualityeducation | 2022 | untagged | MCRMSE | 1 | S1 S2 S3 |  |
| RTA | 2011 | untagged | RMSE | 1 | S1 S2 S3 |  |
| stayalert | 2011 | untagged | AUC | 1 | S1 S2 S3 |  |
| twitter-personality-prediction | 2012 | untagged | MCAP | 1 | S1 S2 S3 |  |
| twitter-psychopathy-prediction | 2012 | untagged | MCAP | 1 | S1 S2 S3 |  |
| unemployment-rate | 2020 | untagged | RMSE | 1 | S1 S2 S3 | non_english, thin_dataset_desc |
| womens-machine-learning-competition-2018 | 2018 | untagged | LogLoss | 1 | S1 S2 S3 |  |

### B. Borderline: metric tabular-ish (S1), not hard-excluded, but rejected

| slug | year | class | metric | writeups | signals | why rejected |
|---|---|---|---|---|---|---|
| csiro-biomass | 2026 | other_tags | R2 Score (#39243596) | 36 | S1 | media_ext:2; media_kw:img |
| alaska2-image-steganalysis | 2020 | untagged | WeightedAUC | 13 | S1 S2 | media_kw:img |
| tensorflow-speech-recognition-challenge | 2018 | untagged | CategorizationAccuracy | 10 | S1 | media_ext:6; media_kw:aud |
| landmark-retrieval-2019 | 2019 | untagged | MAP@{K} | 8 | S1 S2 | media_kw:img |
| cdiscount-image-classification-challenge | 2017 | other_tags | CategorizationAccuracy | 7 | S1 S2 S4 | media_kw:img |
| ultra-mnist | 2022 | untagged | CategorizationAccuracy | 7 | S1 S2 | media_kw:img |
| connectomics | 2014 | untagged | AUC | 6 | S1 S3 | no tabular-file mention and no positive tag |
| histopathologic-cancer-detection | 2019 | other_tags | AUC | 5 | S1 S2 | media_kw:img |
| iwildcam-2020-fgvc7 | 2020 | other_tags | CategorizationAccuracy | 5 | S1 S4 | media_kw:img |
| melbourne-university-seizure-prediction | 2016 | other_tags | AUC | 5 | S1 S4 | media_kw:aud |
| seizure-prediction | 2014 | untagged | AUC | 5 | S1 | media_kw:aud |
| widsdatathon2022 | 2022 | untagged | RMSE | 5 | S1 S3 | no tabular-file mention and no positive tag |
| mlsp-2014-mri | 2014 | untagged | AUC | 4 | S1 | media_ext:4; media_kw:img |
| vehicle | 2019 | untagged | CategorizationAccuracy | 4 | S1 | media_ext:1; media_kw:img |
| widsdatathon2019 | 2019 | untagged | AUC | 4 | S1 | media_ext:2; media_kw:img |
| cassava-disease | 2019 | untagged | CategorizationAccuracy | 3 | S1 S2 | media_kw:img |
| emc-data-science | 2012 | untagged | MulticlassLossOld | 3 | S1 S3 | no tabular-file mention and no positive tag |
| freesound-audio-tagging | 2018 | untagged | MAP@{K} | 3 | S1 | media_ext:2; media_kw:aud |
| grasp-and-lift-eeg-detection | 2015 | other_tags | MCAUC | 3 | S1 S2 S4 | media_kw:aud |
| imaterialist-challenge-fashion-2018 | 2018 | untagged | FScoreBetaMicro | 3 | S1 S2 | media_kw:img |
| ml-olympiad-landscape-image-classification | 2022 | untagged | CategorizationAccuracy | 3 | S1 | media_ext:2; media_kw:img |
| see-click-predict-fix | 2013 | untagged | RMSLE | 3 | S1 S3 | no tabular-file mention and no positive tag |
| avito-duplicate-ads-detection | 2016 | other_tags | AUC | 2 | S1 | media_ext:1; media_kw:img |
| congressionaltweetcompetitionspring2022 | 2022 | untagged | CategorizationAccuracy | 2 | S1 S2 | media_kw:txt |
| dunnhumbychallenge | 2011 | untagged | PercentCorrectVisits | 2 | S1 S3 | no tabular-file mention and no positive tag |
| inria-bci-challenge | 2015 | untagged | AUC | 2 | S1 S2 | media_kw:aud |
| kaggle-pog-series-s01e02 | 2022 | untagged | FScoreMicro | 2 | S1 | media_ext:2; media_kw:aud |
| seizure-detection | 2014 | untagged | MCAUC | 2 | S1 | media_kw:aud |
| the-icml-2013-whale-challenge-right-whale-redux | 2013 | untagged | AUC | 2 | S1 | media_ext:4 |
| tsp-cv | 2022 | untagged | RMSE | 2 | S1 | media_ext:1; media_kw:img |
| unimelb | 2011 | untagged | AUC | 2 | S1 S2 | media_kw:txt |
| wise-2014 | 2014 | untagged | FScoreMicro | 2 | S1 | media_kw:txt |
| 108-2-dl-app-hw1 | 2020 | untagged | CategorizationAccuracy | 1 | S1 S3 | no tabular-file mention and no positive tag |
| 2021aisoftware | 2021 | untagged | CategorizationAccuracy | 1 | S1 S3 | no tabular-file mention and no positive tag |
| allstate-purchase-prediction-challenge | 2014 | untagged | CategorizationAccuracy | 1 | S1 S3 | no tabular-file mention and no positive tag |
| bioresponse | 2012 | untagged | LogLoss | 1 | S1 S3 | no tabular-file mention and no positive tag |
| classify-leaves | 2021 | untagged | CategorizationAccuracy | 1 | S1 | media_ext:1 |
| conway-s-reverse-game-of-life | 2014 | untagged | MAE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| crowdflower-weather-twitter | 2013 | untagged | RMSE | 1 | S1 | media_kw:txt |
| decoding-the-human-brain | 2014 | untagged | CategorizationAccuracy | 1 | S1 S2 | media_kw:aud |
| denoising-shabby-pages | 2023 | untagged | RMSE | 1 | S1 S2 | media_kw:img |
| detecting-insults-in-social-commentary | 2012 | untagged | AUC | 1 | S1 | media_kw:txt |
| dlinnlp-spring-2019-clf | 2019 | untagged | FScoreMicro | 1 | S1 S2 | media_kw:txt |
| dog-vs-cat-classification | 2022 | untagged | CategorizationAccuracy | 1 | S1 | media_ext:1; media_kw:img |
| dsm2017 | 2017 | untagged | AUC | 1 | S1 S3 | no tabular-file mention and no positive tag |
| emvic | 2012 | untagged | MulticlassLossOld | 1 | S1 S3 | no tabular-file mention and no positive tag |
| evohackaton | 2020 | untagged | CategorizationAccuracy | 1 | S1 | media_ext:3; media_kw:img |
| expedia-personalized-sort | 2013 | untagged | NDCG@{K} | 1 | S1 S2 | media_kw:txt |
| facebook-recruiting-iii-keyword-extraction | 2013 | untagged | FScoreMicro | 1 | S1 S2 | media_kw:txt |
| fired-area-prediction | 2020 | untagged | RMSE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| galaxy-zoo-the-galaxy-challenge | 2014 | untagged | RMSE | 1 | S1 | media_kw:img |
| intercampusai2019 | 2019 | untagged | FScoreMicro | 1 | S1 S3 | no tabular-file mention and no positive tag |
| kdd-cup-2014-predicting-excitement-at-donors-choose | 2014 | untagged | AUC | 1 | S1 S2 | media_kw:txt |
| liberty-mutual-fire-peril | 2014 | untagged | NormalizedWeightedGini | 1 | S1 S3 | no tabular-file mention and no positive tag |
| lshtc | 2014 | untagged | FScoreMacro | 1 | S1 | media_kw:txt |
| mdm | 2011 | untagged | RMSE | 1 | S1 | media_ext:2; media_kw:img |
| mlsp-2013-birds | 2013 | untagged | AUC | 1 | S1 | media_ext:2; media_kw:img,aud |
| msdchallenge | 2012 | untagged | MAP@k | 1 | S1 S3 | no tabular-file mention and no positive tag |
| multilabel-bird-species-classification-nips2013 | 2013 | untagged | AUC | 1 | S1 | media_ext:1; media_kw:aud |
| MusicHackathon | 2012 | untagged | RMSE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| online-sales | 2012 | untagged | RMSLE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| overfitting | 2011 | untagged | AUC | 1 | S1 S3 | no tabular-file mention and no positive tag |
| Raising-Money-to-Fund-an-Organizational-Mission | 2012 | untagged | AverageAmongTopP | 1 | S1 S3 | no tabular-file mention and no positive tag |
| SemiSupervisedFeatureLearning | 2011 | untagged | AUC | 1 | S1 S3 | no tabular-file mention and no positive tag |
| sms-spam-classification | 2016 | untagged | AUC | 1 | S1 S3 | no tabular-file mention and no positive tag |
| the-seeclickfix-311-challenge | 2013 | untagged | RMSLE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| tradeshift-text-classification | 2014 | untagged | LogLoss | 1 | S1 S2 | media_kw:txt |
| two-sigma-financial-news | 2019 | other_tags | TwoSigmaNews | 1 | S1 S4 | media_kw:txt |
| ucsd-dsc190-wi21-introduction-to-data-mining | 2021 | untagged | RMSE | 1 | S1 S3 | no tabular-file mention and no positive tag |
| unifesp-x-ray-body-part-classifier | 2022 | untagged | FScoreMicro | 1 | S1 S2 | media_kw:img |
| yandex-personalized-web-search-challenge | 2014 | untagged | NDCG@{K} | 1 | S1 S3 | no tabular-file mention and no positive tag |
| yelp-recruiting | 2013 | untagged | RMSLE | 1 | S1 S2 | media_kw:txt |
| ykc-cup-1st | 2020 | untagged | RMSE | 1 | S1 S3 | no tabular-file mention and no positive tag |

### C. Borderline: metric unknown/custom, tabular-looking (S2 ∧ S3), not hard-excluded

| slug | year | metric | writeups | signals |
|---|---|---|---|---|
| aiquest-bangla-sentiment-analysis-competition | 2025 | metric_template (#78226469) | 1 | S2 |
| autonomous-agent-prediction-beta | 2026 | Autonomous Agent Prediction Beta Metric (#126146754) | 3 | S2 S3 |
| leash-BELKA | 2024 | Leash Average mAP (#57273273) | 11 | S2 S3 S4 |

### D. Hard-excluded (S5) — obvious non-tabular

| slug | year | metric | writeups | reasons |
|---|---|---|---|---|
| ai-agent-security-multi-step-tool-attacks | 2026 | Agents Security Metric (#122642336) | 102 | metric:Agents Security Metric; media_kw:txt |
| rogii-wellbore-geology-prediction | 2026 | Mean Squared Error (#39243534) | 65 | tags:multimodal; media_ext:1 |
| birdclef-2026 | 2026 | Birdclef ROC AUC (#52665836) | 45 | metric:Birdclef ROC AUC; tags:audio event classification; media_ext:4; media_kw:aud |
| ai-village-capture-the-flag-defcon31 | 2023 | Flag_Metric (#43391374) | 42 | metric:Flag_Metric; tags:adversarial learning |
| nvidia-nemotron-model-reasoning-challenge | 2026 | NVIDIA Nemotron Metric (#109982711) | 38 | metric:NVIDIA Nemotron Metric; tags:deep learning,general knowledge and reasoning,pre-trained model |
| kaggriculture | 2026 | kaggriculture | 34 | metric:kaggriculture; tags:simulations |
| llm-detect-ai-generated-text | 2024 | Roc Auc Score (#39244492) | 32 | tags:text generation; media_kw:txt |
| neurogolf-2026 | 2026 | NeuroGolf Metric (#115666188) | 32 | metric:NeuroGolf Metric; tags:neural networks,optimization; media_kw:img |
| santa-2025 | 2026 | Santa 2025 Metric (#97141239) | 29 | metric:Santa 2025 Metric; tags:optimization |
| asl-fingerspelling | 2023 | PostProcessorKernelDesc | 28 | metric:PostProcessorKernelDesc; tags:video classification |
| LANL-Earthquake-Prediction | 2019 | MAE | 28 | tags:signal processing |
| vesuvius-challenge-surface-detection | 2026 | Vesuvius 2025 Metric (#96973679) | 28 | metric:Vesuvius 2025 Metric; tags:image segmentation,segmentation |
| orbit-wars | 2026 | orbit_wars | 27 | metric:orbit_wars; tags:reinforcement learning,simulations |
| pii-detection-removal-from-educational-data | 2024 | TLAL_F_beta (#48933658) | 26 | metric:TLAL_F_beta; tags:text classification; media_kw:txt |
| predict-ai-model-runtime | 2023 | 58266_TpuGraphsEval (#42603795) | 24 | metric:58266_TpuGraphsEval; tags:graph neural network,tpu |
| make-data-count-finding-data-references | 2025 | 82370_MDC_Global_F1 (#84751785) | 23 | metric:82370_MDC_Global_F1; tags:text mining; media_kw:txt |
| ariel-data-challenge-2024 | 2024 | Ariel Gaussian Log Likelihood (#62368338) | 22 | metric:Ariel Gaussian Log Likelihood; tags:multimodal; media_kw:img |
| ariel-data-challenge-2025 | 2025 | Ariel Gaussian Log Likelihood (#62368338) | 22 | metric:Ariel Gaussian Log Likelihood; tags:multimodal; media_kw:img |
| hubmap-hacking-the-human-vasculature | 2023 | OpenImagesObjDetectionSegmentationAP | 21 | metric:OpenImagesObjDetectionSegmentationAP; tags:image segmentation; media_kw:img |
| indoor-location-navigation | 2021 | IndoorLocalization | 21 | metric:IndoorLocalization; tags:signal processing,text mining; media_ext:1 |
| asl-signs | 2023 | PostProcessorKernelDesc | 20 | metric:PostProcessorKernelDesc; tags:video classification |
| waveform-inversion | 2025 | Mean Absolute Error (#39243586) | 20 | tags:signal processing; media_kw:aud |
| g2net-gravitational-wave-detection | 2021 | AUC | 19 | tags:signal processing |
| rsna-breast-cancer-detection | 2023 | ProbFScoreBetaMicro | 19 | tags:image classification; media_ext:1; media_kw:img; metric_unknown |
| stanford-rna-3d-folding-2 | 2026 | Ribonanza TM-Score PermuteChains (#106017268) | 19 | metric:Ribonanza TM-Score PermuteChains |
| birdclef-2025 | 2025 | Birdclef ROC AUC (#52665836) | 18 | metric:Birdclef ROC AUC; tags:audio event classification; media_ext:4; media_kw:aud |
| rock-paper-scissors | 2021 | rps | 18 | metric:rps; tags:simulations |
| llms-you-cant-please-them-all | 2025 | LLMYCPTA metric 20241120 (#72209307) | 17 | metric:LLMYCPTA metric 20241120; tags:text generation; media_kw:txt |
| pokemon-tcg-ai-battle | 2026 | cabt | 17 | metric:cabt; tags:reinforcement learning |
| ai-village-ctf | 2022 | NvidiaDefconWeightedCategorizationAccuracy | 16 | metric:NvidiaDefconWeightedCategorizationAccuracy; tags:adversarial learning |
| seti-breakthrough-listen | 2021 | AUC | 16 | tags:signal processing |
| rsna-intracranial-aneurysm-detection | 2025 | Mean Weighted Columnwise AUCROC (#86873747) | 15 | tags:image classification; media_ext:1; media_kw:img |
| santa-2021 | 2022 | SantasSuperpermutations2021 | 15 | metric:SantasSuperpermutations2021; tags:optimization |
| g2net-detecting-continuous-gravitational-waves | 2023 | AUC | 14 | tags:signal processing |
| nfl-health-and-safety-helmet-assignment | 2021 | NFLHelmetIdentification | 14 | metric:NFLHelmetIdentification; media_kw:img,vid |
| vesuvius-challenge-ink-detection | 2023 | DiceFBeta | 14 | metric:DiceFBeta; tags:image segmentation,image text recognition; media_ext:4 |
| generative-dog-images | 2019 | PostProcessorKernel | 13 | metric:PostProcessorKernel; media_kw:img |
| lmsys-chatbot-arena | 2024 | Log Loss (#39244296) | 13 | tags:languages,text conversation; media_kw:txt |
| lux-ai-season-3 | 2025 | lux_ai_s3 | 13 | metric:lux_ai_s3; tags:reinforcement learning,simulations |
| santa-2024 | 2025 | Santa 2024 Metric (#71069344) | 13 | metric:Santa 2024 Metric; tags:optimization; media_kw:txt |
| data-science-bowl-2018 | 2018 | IntersectionOverUnionObjectSegmentation | 12 | metric:IntersectionOverUnionObjectSegmentation; media_kw:img |
| google-code-golf-2025 | 2025 | Code Golf Metric (#81376142) | 12 | metric:Code Golf Metric; tags:optimization |
| lux-ai-season-2 | 2023 | lux_ai_s2 | 12 | metric:lux_ai_s2; tags:simulations |
| stanford-rna-3d-folding | 2025 | Ribonanza TM-Score (#77405771) | 12 | metric:Ribonanza TM-Score |
| arc-prize-2025 | 2025 | Abstraction and Reasoning Challenge (#58528658) | 11 | metric:Abstraction and Reasoning Challenge |
| neurips-2023-machine-unlearning | 2023 | 56167-unlearn-metric (#42009344) | 11 | metric:56167-unlearn-metric; tags:deep learning; media_ext:2; media_kw:img |
| abstraction-and-reasoning-challenge | 2020 | MeanBestErrorAtK | 10 | metric:MeanBestErrorAtK |
| santa-2023 | 2024 | Santa 2023 Metric (#48030576) | 10 | metric:Santa 2023 Metric; tags:optimization |
| arc-prize-2024 | 2024 | Abstraction and Reasoning Challenge (#58528658) | 9 | metric:Abstraction and Reasoning Challenge |
| cafa-5-protein-function-prediction | 2023 | PostProcessorKernelDesc | 9 | metric:PostProcessorKernelDesc |
| kore-2022 | 2022 | kore_fleets | 9 | metric:kore_fleets; tags:simulations |
| landmark-recognition-2019 | 2019 | GoogleGlobalAP | 9 | metric:GoogleGlobalAP; media_kw:img |
| predict-volcanic-eruptions-ingv-oe | 2021 | MAE | 9 | tags:signal processing |
| fide-google-efficiency-chess-ai-challenge | 2025 | chess | 8 | metric:chess; tags:reinforcement learning,simulations |
| hungry-geese | 2021 | hungry_geese | 8 | metric:hungry_geese; tags:simulations |
| wsdm-cup-multilingual-chatbot-arena | 2025 | Accuracy Score (#39243584) | 8 | tags:languages,text conversation; media_kw:txt |
| google-ai-open-images-object-detection-track | 2018 | OpenImagesObjectDetectionAP | 7 | metric:OpenImagesObjectDetectionAP; media_kw:img |
| konwinski-prize | 2025 | K Prize Metric (#71436031) | 7 | metric:K Prize Metric |
| google-ai-open-images-visual-relationship-track | 2018 | OpenImagesVisualRelations | 6 | metric:OpenImagesVisualRelations; media_kw:img |
| conways-reverse-game-of-life-2020 | 2020 | PostProcessorKernel | 5 | metric:PostProcessorKernel; tags:simulations |
| google-football | 2020 | football | 5 | metric:football; tags:reinforcement learning,simulations |
| imaterialist-fashion-2019-FGVC6 | 2019 | IntersectionOverUnionObjectSegmentationWithClassification | 5 | metric:IntersectionOverUnionObjectSegmentationWithClassification; media_kw:img |
| lux-ai-2021 | 2021 | lux_ai_2021 | 5 | metric:lux_ai_2021; tags:simulations |
| santa-2022 | 2023 | SantasPrintShop2022 | 5 | metric:SantasPrintShop2022; tags:optimization; media_ext:1; media_kw:img |
| santa-gift-matching | 2018 | SantaResident | 5 | metric:SantaResident |
| santa-workshop-tour-2019 | 2020 | SantaWorkshopSchedule2019 | 5 | metric:SantaWorkshopSchedule2019; tags:optimization |
| traveling-santa-2018-prime-paths | 2019 | TravelingSanta2 | 5 | metric:TravelingSanta2; tags:optimization |
| halite | 2020 | halite | 4 | metric:halite; tags:simulations |
| maze-crawler | 2026 | crawl | 4 | metric:crawl; tags:reinforcement learning,simulations |
| santa-2020 | 2021 | mab | 4 | metric:mab; tags:optimization |
| cvpr-2018-autonomous-driving | 2018 | CVPRAutoDrivingAveragePrecision | 3 | metric:CVPRAutoDrivingAveragePrecision; media_kw:img,vid |
| DarkWorlds | 2012 | DarkWorldsMetric | 3 | metric:DarkWorldsMetric |
| hashcode-drone-delivery | 2020 | PostProcessorKernelDesc | 3 | metric:PostProcessorKernelDesc; tags:optimization |
| santa-2019-revenge-of-the-accountants | 2020 | SantaWorkshopSchedule2019Revenge | 3 | metric:SantaWorkshopSchedule2019Revenge; tags:optimization |
| traveling-santa-problem | 2013 | TravelingSanta | 3 | metric:TravelingSanta |
| hashcode-photo-slideshow | 2020 | PostProcessorKernelDesc | 2 | metric:PostProcessorKernelDesc; tags:optimization; media_kw:img |
| helping-santas-helpers | 2015 | SantaJobScheduling | 2 | metric:SantaJobScheduling |
| imaterialist-challenge-furniture-2018 | 2018 | MeanBestErrorAtK | 2 | metric:MeanBestErrorAtK; media_kw:img |
| imaterialist-product-2019 | 2019 | MeanBestErrorAtK | 2 | metric:MeanBestErrorAtK; media_kw:img |
| kore-2022-beta | 2022 | kore_fleets | 2 | metric:kore_fleets |
| semi-inat-2020 | 2020 | MeanBestErrorAtK | 2 | metric:MeanBestErrorAtK |
| spooky-author-identification | 2017 | MulticlassLoss | 2 | tags:linguistics,literature; media_kw:txt |
| 2023-kaggle-ai-report | 2023 | Mean Absolute Error (#39243586) | 1 | tags:deep learning; media_kw:txt |
| body-morphometry-for-sarcopenia | 2020 | Dice | 1 | metric:Dice |
| cause-effect-pairs | 2013 | CauseEffectBidirectionalAuc | 1 | metric:CauseEffectBidirectionalAuc |
| flight2-milestone | 2013 | GE-FQ2 | 1 | metric:GE-FQ2 |
| ifood2018 | 2018 | MeanBestErrorAtK | 1 | metric:MeanBestErrorAtK |
| imaterialist-fashion-2020-fgvc7 | 2020 | IntersectionOverUnionObjectSegmentationWithF1 | 1 | metric:IntersectionOverUnionObjectSegmentationWithF1; media_kw:img |
| learning-social-circles | 2014 | FacebookCircles | 1 | metric:FacebookCircles |
| lux-ai-season-2-neurips-stage-2 | 2023 | lux_ai_s2 | 1 | metric:lux_ai_s2; tags:simulations |
