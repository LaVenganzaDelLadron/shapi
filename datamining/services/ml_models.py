from statistics import median

import numpy as np
from django.core.cache import cache
from django.db.models import Count, Max
from sklearn.linear_model import LinearRegression
from sklearn.metrics import f1_score, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from datamining.models import PigMLData


KNN_NEIGHBORS = [3, 5, 7, 9, 11]
KNN_WEIGHTS = ['uniform', 'distance']
MODEL_CACHE_TIMEOUT = 600

REGRESSION_FEATURES = [
    'pig_age_days',
    'total_feed_quantity',
    'feeding_count',
    'avg_feeding_interval_hours',
]

CLASSIFICATION_FEATURES = [
    'pig_age_days',
    'avg_weight',
    'feeding_count',
    'total_feed_quantity',
]


def _dataset_signature():
    dataset_meta = PigMLData.objects.aggregate(
        row_count=Count('id'),
        latest_updated_at=Max('updated_at'),
    )
    row_count = dataset_meta['row_count'] or 0
    if row_count == 0:
        raise ValueError('PigMLData is empty. Build the dataset before requesting predictions.')

    latest_updated_at = dataset_meta['latest_updated_at']
    latest_token = latest_updated_at.isoformat() if latest_updated_at else 'none'
    return f'{row_count}:{latest_token}'


def _load_numeric_dataset(feature_columns, include_target=None):
    columns = list(feature_columns)
    if include_target:
        columns.append(include_target)

    queryset = PigMLData.objects.all()
    for column in columns:
        queryset = queryset.filter(**{f'{column}__isnull': False})

    rows = list(queryset.values_list(*columns))
    if not rows:
        raise ValueError('PigMLData does not contain enough clean rows for model training.')

    return np.asarray(rows, dtype=float)


def _load_regression_arrays():
    rows = _load_numeric_dataset(REGRESSION_FEATURES, include_target='avg_weight')
    features = rows[:, : len(REGRESSION_FEATURES)]
    target = rows[:, -1]
    return features, target


def _build_classification_targets():
    rows = np.asarray(
        list(PigMLData.objects.values_list('pig_age_days', 'avg_weight', 'feeding_count', 'total_feed_quantity')),
        dtype=float,
    )
    if len(rows) == 0:
        raise ValueError('PigMLData is empty. Build the dataset before requesting predictions.')

    ages = rows[:, 0].reshape(-1, 1)
    weights = rows[:, 1]

    baseline_model = LinearRegression()
    baseline_model.fit(ages, weights)
    expected_weights = baseline_model.predict(ages)
    residuals = weights - expected_weights

    lower_threshold = float(np.quantile(residuals, 0.33))
    upper_threshold = float(np.quantile(residuals, 0.67))

    weight_class = np.where(
        residuals <= lower_threshold,
        'underweight',
        np.where(residuals >= upper_threshold, 'overweight', 'normal'),
    )
    low_growth_risk = np.where(weight_class == 'underweight', 'at_risk', 'low_risk')
    below_expected = np.where(residuals < 0, 'below_expected', 'on_or_above_expected')

    features = rows[:, : len(CLASSIFICATION_FEATURES)]
    targets = {
        'low_growth_risk': low_growth_risk,
        'weight_class': weight_class,
        'below_expected_weight_for_age': below_expected,
    }
    return features, targets


def _best_knn_regressor(features, target):
    if len(features) < 10:
        raise ValueError('At least 10 PigMLData rows are required to train the KNN regressor.')

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
    )

    best_bundle = None
    for k_value in KNN_NEIGHBORS:
        for weights in KNN_WEIGHTS:
            if k_value > len(x_train):
                continue
            model = Pipeline(
                [
                    ('scaler', StandardScaler()),
                    ('model', KNeighborsRegressor(n_neighbors=k_value, weights=weights)),
                ]
            )
            model.fit(x_train, y_train)
            predictions = model.predict(x_test)
            score = r2_score(y_test, predictions)
            candidate = {
                'model': model,
                'k': k_value,
                'weights': weights,
                'score': float(score),
            }
            if best_bundle is None or candidate['score'] > best_bundle['score']:
                best_bundle = candidate

    if best_bundle is None:
        raise ValueError('PigMLData does not contain enough rows to evaluate the requested KNN settings.')

    best_bundle['model'].fit(features, target)
    return best_bundle


def _best_knn_classifier(features, target_values):
    if len(features) < 10:
        raise ValueError('At least 10 PigMLData rows are required to train the KNN classifier.')

    unique_values, counts = np.unique(target_values, return_counts=True)
    if len(unique_values) < 2:
        raise ValueError('The selected classification target does not contain enough label variation.')

    stratify_target = target_values if counts.min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target_values,
        test_size=0.2,
        random_state=42,
        stratify=stratify_target,
    )

    best_bundle = None
    for k_value in KNN_NEIGHBORS:
        for weights in KNN_WEIGHTS:
            if k_value > len(x_train):
                continue
            model = Pipeline(
                [
                    ('scaler', StandardScaler()),
                    ('model', KNeighborsClassifier(n_neighbors=k_value, weights=weights)),
                ]
            )
            model.fit(x_train, y_train)
            predictions = model.predict(x_test)
            score = f1_score(y_test, predictions, average='weighted', zero_division=0)
            candidate = {
                'model': model,
                'k': k_value,
                'weights': weights,
                'score': float(score),
            }
            if best_bundle is None or candidate['score'] > best_bundle['score']:
                best_bundle = candidate

    if best_bundle is None:
        raise ValueError('PigMLData does not contain enough rows to evaluate the requested KNN settings.')

    best_bundle['model'].fit(features, target_values)
    return best_bundle


def train_knn_regressor():
    cache_key = f'knn_regressor:{_dataset_signature()}'
    cached_model = cache.get(cache_key)
    if cached_model is not None:
        return cached_model

    features, target = _load_regression_arrays()
    model_bundle = _best_knn_regressor(features, target)
    cache.set(cache_key, model_bundle, MODEL_CACHE_TIMEOUT)
    return model_bundle


def train_knn_classifier():
    cache_key = f'knn_classifier:{_dataset_signature()}'
    cached_model = cache.get(cache_key)
    if cached_model is not None:
        return cached_model

    features, targets = _build_classification_targets()
    model_bundle = {}
    for target_name, target_values in targets.items():
        model_bundle[target_name] = _best_knn_classifier(features, target_values)

    cache.set(cache_key, model_bundle, MODEL_CACHE_TIMEOUT)
    return model_bundle


def predict_weight(input_data):
    model_bundle = train_knn_regressor()
    feature_vector = np.asarray(
        [[float(input_data[column]) for column in REGRESSION_FEATURES]],
        dtype=float,
    )
    predicted_weight = float(model_bundle['model'].predict(feature_vector)[0])
    return {
        'predicted_weight': round(predicted_weight, 2),
        'model_used': 'KNN',
        'k': model_bundle['k'],
    }


def classify_risk(input_data):
    model_bundle = train_knn_classifier()
    feature_vector = np.asarray(
        [[float(input_data[column]) for column in CLASSIFICATION_FEATURES]],
        dtype=float,
    )

    low_growth_risk_label = model_bundle['low_growth_risk']['model'].predict(feature_vector)[0]
    weight_class_label = model_bundle['weight_class']['model'].predict(feature_vector)[0]
    below_expected_label = model_bundle['below_expected_weight_for_age']['model'].predict(feature_vector)[0]

    return {
        'low_growth_risk': low_growth_risk_label == 'low_risk',
        'weight_class': str(weight_class_label),
        'below_expected': below_expected_label == 'below_expected',
    }


def _similar_age_rows(pig_age_days):
    lower_bound = max(0, pig_age_days - 7)
    upper_bound = pig_age_days + 7
    rows = list(
        PigMLData.objects.filter(pig_age_days__gte=lower_bound, pig_age_days__lte=upper_bound).values_list(
            'feeding_count',
            'total_feed_quantity',
            'avg_feeding_interval_hours',
        )
    )
    if rows:
        return rows

    return list(
        PigMLData.objects.values_list(
            'feeding_count',
            'total_feed_quantity',
            'avg_feeding_interval_hours',
        )
    )


def suggest_feeding_adjustments(current_weight, target_weight, pig_age_days):
    rows = _similar_age_rows(pig_age_days)
    if not rows:
        raise ValueError('PigMLData is empty. Build the dataset before requesting feeding suggestions.')

    feeding_counts = [int(row[0]) for row in rows if row[0] is not None]
    total_feed_values = [float(row[1]) for row in rows if row[1] is not None]
    interval_values = [float(row[2]) for row in rows if row[2] is not None]

    baseline_feeding_count = int(round(median(feeding_counts or [3])))
    baseline_total_feed = float(median(total_feed_values or [2.5]))
    baseline_interval = float(median(interval_values or [8.0]))

    weight_gap = float(target_weight) - float(current_weight)
    recommended_feeding_count = baseline_feeding_count
    recommended_total_feed = baseline_total_feed
    recommended_interval_hours = baseline_interval
    reason = 'Maintain the current feeding plan because the target is already being met.'

    if weight_gap > 0.5:
        increase_steps = 2 if weight_gap > 5 else 1
        recommended_feeding_count = min(5, baseline_feeding_count + increase_steps)
        recommended_total_feed = baseline_total_feed * (1 + min(0.25, weight_gap / 20))
        recommended_interval_hours = max(4.0, 24 / recommended_feeding_count)
        reason = 'Increase feeding to reach target weight.'
    elif weight_gap < -0.5:
        recommended_feeding_count = max(2, baseline_feeding_count - 1)
        recommended_total_feed = baseline_total_feed * 0.95
        recommended_interval_hours = min(12.0, max(baseline_interval, 24 / recommended_feeding_count))
        reason = 'Current weight is above target, so maintain or slightly reduce feeding.'

    recommendation = {
        'pig_age_days': int(pig_age_days),
        'feeding_count': int(recommended_feeding_count),
        'total_feed_quantity': round(float(recommended_total_feed), 2),
        'avg_feeding_interval_hours': round(float(recommended_interval_hours), 2),
    }
    predicted = predict_weight(recommendation)

    return {
        'recommended_feeding_count': recommendation['feeding_count'],
        'recommended_total_feed': recommendation['total_feed_quantity'],
        'recommended_interval_hours': recommendation['avg_feeding_interval_hours'],
        'reason': reason,
        'predicted_weight': predicted['predicted_weight'],
    }
