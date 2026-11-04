# P0 Heuristic v0 — Exact Signal Definitions

**Date**: 2026-11-03 | **Research**: [research.md §R6](research.md#r6-p0-heuristic-candidate-proposal-only) | **Rule contract**: [contracts/p0-membership-rules.md](contracts/p0-membership-rules.md)

These are the exact definitions the planning worker used to produce the counts in R6 and the tables in [research-p0-candidates.md](research-p0-candidates.md): 267-competition pool, 101 candidates, 670 writeups.

Task T023 ports them into `curation/kaggle/p0-rule.yaml` v1.0.0. The port changes four things:

- **Tags become ids.** Tag names here are matched by lowercase name. The rule file must list Tag **ids** and keep each name beside its id, resolved from `Tags.csv` at authoring time.
- **The subject tags are dropped.** `games`, `board games`, `video games`, and `puzzles` are **not** negative tags; the final v0 run removed them from `NEG_TAGS`.
- **Field names change.** `cls` (`untagged` / `other_tags_only`) corresponds to `tag_class` (`untagged` / `other_tags`). `dd` is the dataset description text, `abbr` is the metric abbreviation, and `mname` is the metric name.
- **Thresholds become strings.** They are encoded as strings in YAML and parsed by the rule loader.

The reference-snapshot test (T043) must reproduce **101 candidates** with rule v1.0.0 and an empty reviewed list. A different count means the port diverged and needs explanation.

## Definitions (Python, as run)

```python
import re

TAB_METRIC = re.compile(r'^(RMSE|RMSLE|MAE|MSE|MAPE|SMAPE|R2Score|RValue|NormalizedGini|NormalizedWeightedGini|LogLoss|MulticlassLoss|MulticlassLossOld|WeightedMulticlassLoss|MeanColumnwiseLogLoss|WeightedMeanColumnwiseLogLoss|AUC|MCAUC|WeightedAUC|CategorizationAccuracy|WeightedCategorizationAccuracy|FScoreMacro|FScoreMicro|FScoreBetaMicro|F_\{Beta\} \(deprecated\)|FScore_1 \(deprecated\)|MCRMSE|MCRMSLE|MWCRMSE|MeanColumnwiseMAE|CRPS|WeightedPinballLoss|WeightedRowwisePinballLoss|M5_WRMSSE|SpearmanR|MeanPearson|PearsonCorrelationCoefficient|QuadraticWeightedKappa|MatthewsCorrelationCoefficient|NDCG@\{K\}|MAP@k|MAP@\{K\}|MAP@\{K\}_OLD|WeightedRecall@\{K\}|ZillowMAE|WMAE|NWRMSLE|RootMeanSquarePercentageError|GroupMeanLogMAE|PercentCorrectVisits|AverageAmongTopP|HiggsBosonApproximateMedianSignificance|TwoSigmaNews|JaneStreetPnl|AmexGiniAndPercentageCaptureX|LaplaceLogLikelihood|MCAP|WRRMSE)$')
TAB_METRIC_NAME = re.compile(r'(?i)^(mean squared error|mean absolute error|mean squared log error|r2 score|roc auc score|accuracy score|balanced accuracy score|cohen kappa score|log loss|matthews corrcoef|f1 score|mean absolute percentage error|sklearn_roc_auc_score|sklearn_average_precision_score|kullback leibler divergence|smape_plus_1)$|sharpe|gini|concordance|commodity prediction|march mania|nfl_|polymer|wildfire|zero-mean r2|mean weighted columnwise aucroc')
NONTAB_METRIC = re.compile(r'(?i)santa|^(cabt|chess|crawl|football|halite|hungry_geese|kaggriculture|kore_fleets|lux_ai_2021|lux_ai_s2|lux_ai_s3|mab|orbit_wars|rps|llm_20_questions)$|dice|intersectionoverunion|objectdetection|objdetection|openimages|visualrelations|googleglobalap|meanbesterroratk|levenshtein|bleu|word error rate|postprocessorkernel|abstraction and reasoning|code golf|neurogolf|flag_metric|defcon|tm-score|birdclef|vesuvius|svg image|image fidelity|helmet|autodriving|lyft3d|imc20|image ?matching|maa|nemotron|agents security|k prize|llmycpta|unlearn|aimo|f_beta|tlal|mdc_global|cmap|event detection|cryoet|zebrafish|biophysics|surface dice|aneurysm|recodai|tpugraphs|ariel|darkworlds|facebookcircles|ge-fq2|causeeffect|indoorlocalization|smartphonedecimeter|trackml')
POS_TAGS = {'regression','binary classification','multiclass classification','tabular classification','logistic regression','linear regression','classification','finance','banking','insurance','investing','currencies and foreign exchange','sports','basketball','football','golf','retail and shopping','housing','real estate','recommender systems','categorical','business','marketing','food','energy','healthcare','covid19'}
NEG_TAGS = {'simulations','reinforcement learning','optimization','signal processing','multimodal','text conversation','text generation','text mining','text classification','image segmentation','segmentation','image classification','image text recognition','audio event classification','video classification','adversarial learning','deep learning','pre-trained model','general knowledge and reasoning','graph neural network','tpu','linguistics','literature','languages','neural networks'}
# (games, board games, video games, puzzles removed in the final run)

def strip(s):  # applied to the dataset description before S2/S3
    s = re.sub(r'<img[^>]*>', '', s or '', flags=re.I)
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'https?://\S+', '', s)
    return s

MEDIA_EXT = r'\.(jpe?g|png|tiff?|bmp|dcm|dicom|nii(\.gz)?|svs|wav|mp3|flac|ogg|aiff?|mp4|avi|mov|mkv|tfrecords?)\b'
TABFILE = r'\.(csv|parquet|feather|tsv|xlsx?)\b'
KW = {
    'img': r'\bimages?\b|\bphotos?\b|\bpixels?\b|\bx-rays?\b|\bmri\b|\bct scans?\b|\bmicroscop\w*|\bpictures?\b',
    'aud': r'\baudio\b|\bsounds?\b|\brecordings?\b|\bspectrograms?\b|\beeg\b|\becg\b|\bmeg\b|\bwaveforms?\b|\bspeech\b',
    'vid': r'\bvideos?\b|\bvideo frames?\b',
    'txt': r'\b(essays?|tweets?|sentences?|articles?|reviews?|comments?|corpus|abstracts?|wikipedia|text|prompts?)\b|\bnlp\b|\bllms?\b',
}
BIOSEQ = r'\bsmiles\b|\brna\b|\bdna\b|\bprotein sequences?\b|\bamino acids?\b|\bnucleotides?\b'

def count(p, s): return len(re.findall(p, s, flags=re.I))

# per competition in the pool (tag_class in {untagged, other_tags}):
#   dd = strip(dataset_description); head = title + ' \n ' + subtitle
#   m_neg = NONTAB_METRIC.search(abbr) or NONTAB_METRIC.search(mname)
#   S1 = not m_neg and (TAB_METRIC.match(abbr) or TAB_METRIC_NAME.search(mname))
#   mext = count(MEDIA_EXT, dd); tf = count(TABFILE, dd)
#   media_kw = [k for k in KW if count(KW[k], dd) >= 6 or count(KW[k], head) > 0]
#   S2 = tf > 0 and mext == 0
#   S3 = mext == 0 and not media_kw
#   S4 = bool(tags & POS_TAGS) and not (tags & NEG_TAGS)
#   S5 = m_neg or bool(tags & NEG_TAGS)
#   candidate = not S5 and S1 and S3 and (S2 or S4)
# review flags:
#   bioseq: count(BIOSEQ, dd + head) >= 2
#   non_english: ASCII characters < 70% of head
#   thin_dataset_desc: dataset description absent or len(strip(dd)) < 300
#   signal: 'signal processing' in tags or count(KW['aud'], dd) >= 3
```
