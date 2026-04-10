import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_fscore_support,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor


REQUIRED_COLUMNS = [
    'record_code',
    'batch_code',
    'pen_code',
    'sample_date',
    'pig_age_days',
    'avg_weight',
    'total_feed_quantity',
    'feeding_count',
    'avg_feeding_interval_hours',
    'pen_capacity',
    'pen_status',
    'growth_stage',
    'feed_type_mode',
    'device_code',
    'window_days',
]

NUMERIC_COLUMNS = [
    'pig_age_days',
    'avg_weight',
    'total_feed_quantity',
    'feeding_count',
    'avg_feeding_interval_hours',
    'pen_capacity',
    'window_days',
]

NUMERIC_FEATURE_COLUMNS = [
    'pig_age_days',
    'total_feed_quantity',
    'feeding_count',
    'avg_feeding_interval_hours',
    'pen_capacity',
    'window_days',
]

CATEGORICAL_FEATURE_COLUMNS = [
    'pen_status',
    'growth_stage',
]

MODEL_FEATURE_COLUMNS = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS
KNN_NEIGHBORS = [3, 5, 7, 9, 11]
KNN_WEIGHTS = ['uniform', 'distance']
GROWTH_STAGE_ORDER = ['HOGPRE', 'STARTER', 'GROWER', 'FINISHER']


def print_section(title):
    print(f'\n{"=" * 16} {title} {"=" * 16}')


def load_dataset(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f'Input file not found: {path}')

    if path.suffix.lower() == '.csv':
        dataframe = pd.read_csv(path)
    elif path.suffix.lower() == '.json':
        with path.open('r', encoding='utf-8') as source_file:
            payload = json.load(source_file)
        if isinstance(payload, dict):
            payload = payload.get('data', payload.get('results', []))
        dataframe = pd.DataFrame(payload)
    else:
        raise ValueError('Only .json and .csv files are supported.')

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f'Missing required columns: {missing_columns}')

    dataframe = dataframe.copy()
    dataframe['sample_date'] = pd.to_datetime(dataframe['sample_date'], errors='coerce', utc=True)
    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(dataframe[column], errors='coerce')

    before_drop = len(dataframe)
    dataframe = dataframe.dropna(subset=REQUIRED_COLUMNS)
    dropped_rows = before_drop - len(dataframe)
    if dropped_rows:
        print(f'Dropped {dropped_rows} rows with missing required values.')

    dataframe = dataframe.sort_values('sample_date').reset_index(drop=True)
    return dataframe


def save_plot(output_dir, filename, show_plots):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    if show_plots:
        plt.show()
    plt.close()
    return output_path


def descriptive_analytics(dataframe, output_dir, show_plots):
    print_section('DESCRIPTIVE ANALYTICS')
    print('Dataset shape:', dataframe.shape)
    print('\nColumn types:')
    print(dataframe.dtypes.astype(str).to_string())

    print('\nMissing values:')
    print(dataframe.isna().sum().to_string())

    print('\nNumeric summary:')
    print(dataframe[NUMERIC_COLUMNS].describe().round(2).to_string())

    avg_weight_by_stage = (
        dataframe.groupby('growth_stage', observed=False)['avg_weight']
        .mean()
        .reindex(GROWTH_STAGE_ORDER)
        .dropna()
        .round(2)
    )
    print('\nAverage weight per growth stage:')
    print(avg_weight_by_stage.to_string())

    total_feed_by_batch = (
        dataframe.groupby('batch_code', observed=False)['total_feed_quantity']
        .sum()
        .sort_values(ascending=False)
        .round(2)
    )
    print('\nTotal feed consumption per batch:')
    print(total_feed_by_batch.to_string())

    feeding_trend = (
        dataframe.assign(sample_day=dataframe['sample_date'].dt.floor('D'))
        .groupby('sample_day', observed=False)['feeding_count']
        .mean()
        .round(2)
    )
    print('\nAverage feeding frequency trend by day:')
    print(feeding_trend.to_string())

    plt.figure(figsize=(8, 5))
    avg_weight_by_stage.plot(kind='bar', color='#4C956C')
    plt.title('Average Weight by Growth Stage')
    plt.xlabel('Growth Stage')
    plt.ylabel('Average Weight (kg)')
    save_plot(output_dir, 'descriptive_avg_weight_by_growth_stage.png', show_plots)

    plt.figure(figsize=(10, 5))
    total_feed_by_batch.head(15).sort_values().plot(kind='barh', color='#2C7DA0')
    plt.title('Top Batches by Total Feed Consumption')
    plt.xlabel('Total Feed Quantity')
    plt.ylabel('Batch Code')
    save_plot(output_dir, 'descriptive_total_feed_by_batch.png', show_plots)

    plt.figure(figsize=(10, 5))
    plt.plot(feeding_trend.index, feeding_trend.values, marker='o', color='#D1495B')
    plt.title('Daily Feeding Frequency Trend')
    plt.xlabel('Sample Date')
    plt.ylabel('Average Feeding Count')
    plt.xticks(rotation=30, ha='right')
    save_plot(output_dir, 'descriptive_feeding_frequency_trend.png', show_plots)


def describe_correlation(value):
    absolute_value = abs(value)
    if absolute_value >= 0.7:
        strength = 'strong'
    elif absolute_value >= 0.4:
        strength = 'moderate'
    else:
        strength = 'weak'
    direction = 'positive' if value >= 0 else 'negative'
    return f'{strength} {direction}'


def add_classification_targets(dataframe):
    dataframe = dataframe.copy()
    if 'expected_weight_by_age' not in dataframe.columns:
        age_baseline = LinearRegression()
        age_baseline.fit(dataframe[['pig_age_days']], dataframe['avg_weight'])
        dataframe['expected_weight_by_age'] = age_baseline.predict(dataframe[['pig_age_days']])

    dataframe['weight_residual'] = dataframe['avg_weight'] - dataframe['expected_weight_by_age']

    lower_threshold = dataframe['weight_residual'].quantile(0.33)
    upper_threshold = dataframe['weight_residual'].quantile(0.67)

    dataframe['weight_class'] = np.select(
        [
            dataframe['weight_residual'] <= lower_threshold,
            dataframe['weight_residual'] >= upper_threshold,
        ],
        ['underweight', 'above_target'],
        default='normal',
    )
    dataframe['low_growth_risk'] = np.where(
        dataframe['weight_class'] == 'underweight',
        'at_risk',
        'on_track',
    )
    dataframe['below_expected_weight_for_age'] = np.where(
        dataframe['weight_residual'] < 0,
        'below_expected',
        'on_or_above_expected',
    )
    return dataframe


def diagnostic_analytics(dataframe, output_dir, show_plots):
    print_section('DIAGNOSTIC ANALYTICS')

    grouped_feeding_weight = (
        dataframe.groupby('feeding_count', observed=False)['avg_weight']
        .mean()
        .round(2)
        .sort_index()
    )
    print('Average weight by feeding count:')
    print(grouped_feeding_weight.to_string())

    stage_feed = (
        dataframe.groupby('growth_stage', observed=False)['total_feed_quantity']
        .agg(['mean', 'median', 'min', 'max'])
        .reindex(GROWTH_STAGE_ORDER)
        .round(2)
        .dropna(how='all')
    )
    print('\nTotal feed quantity by growth stage:')
    print(stage_feed.to_string())

    numeric_frame = dataframe[NUMERIC_COLUMNS]
    correlation_matrix = numeric_frame.corr().round(3)
    print('\nCorrelation matrix:')
    print(correlation_matrix.to_string())

    print('\nCorrelation insights:')
    weight_relationships = correlation_matrix['avg_weight'].drop('avg_weight').sort_values(
        key=lambda series: series.abs(),
        ascending=False,
    )
    for feature_name, correlation_value in weight_relationships.items():
        print(
            f'- {feature_name}: {correlation_value:.3f} '
            f'({describe_correlation(correlation_value)} relationship with avg_weight)'
        )

    plt.figure(figsize=(8, 5))
    plt.scatter(
        dataframe['feeding_count'],
        dataframe['avg_weight'],
        alpha=0.65,
        color='#4C956C',
        edgecolors='black',
        linewidths=0.3,
    )
    plt.plot(
        grouped_feeding_weight.index,
        grouped_feeding_weight.values,
        color='#D1495B',
        marker='o',
        linewidth=2,
        label='Average weight by feeding count',
    )
    plt.title('Feeding Count vs Average Weight')
    plt.xlabel('Feeding Count')
    plt.ylabel('Average Weight (kg)')
    plt.legend()
    save_plot(output_dir, 'diagnostic_feeding_count_vs_weight.png', show_plots)

    plt.figure(figsize=(8, 5))
    stage_feed['mean'].plot(kind='bar', color='#2C7DA0')
    plt.title('Average Feed Quantity by Growth Stage')
    plt.xlabel('Growth Stage')
    plt.ylabel('Average Feed Quantity')
    save_plot(output_dir, 'diagnostic_total_feed_by_growth_stage.png', show_plots)

    figure, axis = plt.subplots(figsize=(8, 6))
    image = axis.imshow(correlation_matrix, cmap='coolwarm', vmin=-1, vmax=1)
    axis.set_xticks(range(len(correlation_matrix.columns)))
    axis.set_yticks(range(len(correlation_matrix.index)))
    axis.set_xticklabels(correlation_matrix.columns, rotation=45, ha='right')
    axis.set_yticklabels(correlation_matrix.index)
    axis.set_title('Correlation Matrix')
    for row_index in range(len(correlation_matrix.index)):
        for col_index in range(len(correlation_matrix.columns)):
            axis.text(
                col_index,
                row_index,
                f'{correlation_matrix.iloc[row_index, col_index]:.2f}',
                ha='center',
                va='center',
                color='black',
            )
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    save_plot(output_dir, 'diagnostic_correlation_matrix.png', show_plots)

    age_baseline = LinearRegression()
    age_baseline.fit(dataframe[['pig_age_days']], dataframe['avg_weight'])
    dataframe = dataframe.copy()
    dataframe['expected_weight_by_age'] = age_baseline.predict(dataframe[['pig_age_days']])
    dataframe['weight_residual'] = dataframe['avg_weight'] - dataframe['expected_weight_by_age']

    high_feed_threshold = dataframe['total_feed_quantity'].quantile(0.75)
    low_residual_threshold = dataframe['weight_residual'].quantile(0.20)
    anomalies = (
        dataframe[
            (dataframe['total_feed_quantity'] >= high_feed_threshold)
            & (dataframe['weight_residual'] <= low_residual_threshold)
        ]
        .sort_values(['weight_residual', 'total_feed_quantity'])
        [
            [
                'record_code',
                'pig_age_days',
                'avg_weight',
                'expected_weight_by_age',
                'weight_residual',
                'total_feed_quantity',
                'feeding_count',
                'growth_stage',
            ]
        ]
        .head(10)
    )
    print('\nPotential anomalies: low weight despite high feeding')
    if anomalies.empty:
        print('No clear anomalies found using the current thresholds.')
    else:
        print(anomalies.round(2).to_string(index=False))

    return add_classification_targets(dataframe)


def prepare_feature_matrix(dataframe):
    feature_frame = dataframe[MODEL_FEATURE_COLUMNS].copy()
    for column in CATEGORICAL_FEATURE_COLUMNS:
        feature_frame[column] = feature_frame[column].astype(str)
    return pd.get_dummies(feature_frame, columns=CATEGORICAL_FEATURE_COLUMNS, dtype=float)


def align_feature_matrix(dataframe, reference_columns):
    aligned = prepare_feature_matrix(dataframe)
    return aligned.reindex(columns=reference_columns, fill_value=0.0)


def aggregate_feature_scores(raw_scores):
    aggregated_scores = {}
    for encoded_column, value in raw_scores.items():
        matched = False
        for base_feature in CATEGORICAL_FEATURE_COLUMNS:
            prefix = f'{base_feature}_'
            if encoded_column.startswith(prefix):
                aggregated_scores[base_feature] = aggregated_scores.get(base_feature, 0.0) + abs(float(value))
                matched = True
                break
        if not matched:
            aggregated_scores[encoded_column] = aggregated_scores.get(encoded_column, 0.0) + abs(float(value))
    return pd.Series(aggregated_scores).sort_values(ascending=False)


def extract_feature_importance(model, encoded_columns):
    final_model = model.named_steps['model'] if isinstance(model, Pipeline) else model

    if hasattr(final_model, 'feature_importances_'):
        raw_scores = pd.Series(final_model.feature_importances_, index=encoded_columns)
        return aggregate_feature_scores(raw_scores)

    if hasattr(final_model, 'coef_'):
        coefficients = np.asarray(final_model.coef_)
        if coefficients.ndim > 1:
            coefficients = np.mean(np.abs(coefficients), axis=0)
        else:
            coefficients = np.abs(coefficients)
        raw_scores = pd.Series(coefficients, index=encoded_columns)
        return aggregate_feature_scores(raw_scores)

    return None


def build_regression_models():
    models = {
        'Linear Regression': Pipeline(
            [
                ('scaler', StandardScaler()),
                ('model', LinearRegression()),
            ]
        ),
        'Decision Tree Regressor': DecisionTreeRegressor(
            random_state=42,
            max_depth=6,
            min_samples_leaf=3,
        ),
        'Random Forest Regressor': RandomForestRegressor(
            random_state=42,
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            n_jobs=-1,
        ),
    }

    for neighbors in KNN_NEIGHBORS:
        for weights in KNN_WEIGHTS:
            models[f'KNN Regressor (k={neighbors}, weights={weights})'] = Pipeline(
                [
                    ('scaler', StandardScaler()),
                    ('model', KNeighborsRegressor(n_neighbors=neighbors, weights=weights)),
                ]
            )

    return models


def regression_analytics_module(dataframe, output_dir, show_plots, prediction_sample):
    print_section('REGRESSION ANALYTICS MODULE')

    dataset = dataframe.dropna(subset=MODEL_FEATURE_COLUMNS + ['avg_weight']).copy()
    if len(dataset) < 10:
        raise ValueError('At least 10 clean rows are needed for regression training.')

    encoded_features = prepare_feature_matrix(dataset)
    target = dataset['avg_weight']

    x_train, x_test, y_train, y_test = train_test_split(
        encoded_features,
        target,
        test_size=0.2,
        random_state=42,
    )

    model_library = build_regression_models()
    trained_models = {}
    test_predictions = {}
    results = []

    for model_name, model in model_library.items():
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        trained_models[model_name] = model
        test_predictions[model_name] = predicted
        results.append(
            {
                'model': model_name,
                'r2_score': r2_score(y_test, predicted),
                'rmse': float(np.sqrt(mean_squared_error(y_test, predicted))),
                'mae': mean_absolute_error(y_test, predicted),
            }
        )

    results_frame = pd.DataFrame(results).sort_values(
        ['r2_score', 'rmse', 'mae'],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    best_model_name = results_frame.iloc[0]['model']
    best_model = model_library[best_model_name]
    best_model.fit(encoded_features, target)

    print('Regression model comparison:')
    print(results_frame.round(4).to_string(index=False))
    print(f'\nBest regression model: {best_model_name}')

    sample_frame = pd.DataFrame([prediction_sample], columns=MODEL_FEATURE_COLUMNS)
    aligned_sample = align_feature_matrix(sample_frame, encoded_features.columns)
    predicted_weight = float(best_model.predict(aligned_sample)[0])
    print('\nFuture weight prediction for sample input:')
    print(json.dumps({**prediction_sample, 'predicted_avg_weight': round(predicted_weight, 2)}, indent=2))

    feature_importance = extract_feature_importance(best_model, encoded_features.columns)
    if feature_importance is not None:
        print('\nRegression feature importance:')
        print(feature_importance.round(4).to_string())

        plt.figure(figsize=(8, 5))
        feature_importance.sort_values().plot(kind='barh', color='#4C956C')
        plt.title(f'Regression Feature Importance - {best_model_name}')
        plt.xlabel('Importance Score')
        save_plot(output_dir, 'regression_feature_importance.png', show_plots)

    plt.figure(figsize=(11, 5))
    plt.bar(results_frame['model'], results_frame['r2_score'], color='#2C7DA0')
    plt.title('Regression Model Comparison by R² Score')
    plt.xlabel('Model')
    plt.ylabel('R² Score')
    plt.xticks(rotation=35, ha='right')
    save_plot(output_dir, 'regression_model_comparison.png', show_plots)

    best_test_predictions = test_predictions[best_model_name]
    plt.figure(figsize=(7, 6))
    plt.scatter(
        y_test,
        best_test_predictions,
        color='#2C7DA0',
        alpha=0.7,
        edgecolors='black',
        linewidths=0.3,
    )
    min_value = min(y_test.min(), best_test_predictions.min())
    max_value = max(y_test.max(), best_test_predictions.max())
    plt.plot([min_value, max_value], [min_value, max_value], color='#D1495B', linestyle='--')
    plt.title(f'Actual vs Predicted Weight ({best_model_name})')
    plt.xlabel('Actual Weight (kg)')
    plt.ylabel('Predicted Weight (kg)')
    save_plot(output_dir, 'regression_actual_vs_predicted.png', show_plots)

    return {
        'best_model': best_model,
        'best_model_name': best_model_name,
        'feature_columns': encoded_features.columns.tolist(),
        'results_frame': results_frame,
        'predicted_weight': predicted_weight,
    }


def build_classification_models():
    models = {
        'Logistic Regression': Pipeline(
            [
                ('scaler', StandardScaler()),
                ('model', LogisticRegression(max_iter=2000)),
            ]
        ),
    }

    for neighbors in KNN_NEIGHBORS:
        for weights in KNN_WEIGHTS:
            models[f'KNN Classifier (k={neighbors}, weights={weights})'] = Pipeline(
                [
                    ('scaler', StandardScaler()),
                    ('model', KNeighborsClassifier(n_neighbors=neighbors, weights=weights)),
                ]
            )

    return models


def classification_analytics_module(dataframe, output_dir, show_plots, classification_target):
    print_section('CLASSIFICATION ANALYTICS MODULE')
    print(f'Classification target: {classification_target}')

    dataset = dataframe.dropna(subset=MODEL_FEATURE_COLUMNS + [classification_target]).copy()
    if len(dataset) < 10:
        raise ValueError('At least 10 clean rows are needed for classification training.')

    encoded_features = prepare_feature_matrix(dataset)
    target = dataset[classification_target].astype(str)
    class_counts = target.value_counts().sort_index()
    print('\nTarget class distribution:')
    print(class_counts.to_string())

    if target.nunique() < 2:
        raise ValueError(f'Target "{classification_target}" must contain at least two classes.')

    stratify_target = target if class_counts.min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        encoded_features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=stratify_target,
    )

    model_library = build_classification_models()
    trained_models = {}
    confusion_matrices = {}
    evaluation_rows = []
    labels = sorted(target.unique().tolist())

    for model_name, model in model_library.items():
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        trained_models[model_name] = model
        confusion_matrices[model_name] = confusion_matrix(y_test, predicted, labels=labels)
        precision, recall, f1_score, _ = precision_recall_fscore_support(
            y_test,
            predicted,
            average='weighted',
            zero_division=0,
        )
        evaluation_rows.append(
            {
                'model': model_name,
                'accuracy': accuracy_score(y_test, predicted),
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
            }
        )

    results_frame = pd.DataFrame(evaluation_rows).sort_values(
        ['f1_score', 'accuracy', 'precision', 'recall'],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    best_model_name = results_frame.iloc[0]['model']
    best_model = model_library[best_model_name]
    best_model.fit(encoded_features, target)

    print('\nClassification model comparison:')
    print(results_frame.round(4).to_string(index=False))
    print(f'\nBest classification model: {best_model_name}')

    best_confusion_matrix = confusion_matrices[best_model_name]
    confusion_frame = pd.DataFrame(best_confusion_matrix, index=labels, columns=labels)
    print('\nConfusion matrix for best classification model:')
    print(confusion_frame.to_string())

    plt.figure(figsize=(11, 5))
    plt.bar(results_frame['model'], results_frame['f1_score'], color='#D1495B')
    plt.title('Classification Model Comparison by Weighted F1 Score')
    plt.xlabel('Model')
    plt.ylabel('Weighted F1 Score')
    plt.xticks(rotation=35, ha='right')
    save_plot(output_dir, 'classification_model_comparison.png', show_plots)

    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(best_confusion_matrix, cmap='Blues')
    axis.set_xticks(range(len(labels)))
    axis.set_yticks(range(len(labels)))
    axis.set_xticklabels(labels, rotation=30, ha='right')
    axis.set_yticklabels(labels)
    axis.set_xlabel('Predicted Label')
    axis.set_ylabel('True Label')
    axis.set_title(f'Confusion Matrix - {best_model_name}')
    for row_index in range(len(labels)):
        for col_index in range(len(labels)):
            axis.text(
                col_index,
                row_index,
                str(best_confusion_matrix[row_index, col_index]),
                ha='center',
                va='center',
                color='black',
            )
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    save_plot(output_dir, 'classification_confusion_matrix.png', show_plots)

    return {
        'best_model_name': best_model_name,
        'results_frame': results_frame,
        'confusion_matrix': confusion_frame,
    }


def infer_growth_stage(age_days):
    if age_days <= 44:
        return 'HOGPRE'
    if age_days <= 69:
        return 'STARTER'
    if age_days <= 109:
        return 'GROWER'
    return 'FINISHER'


def build_default_prediction_sample(dataframe):
    age_value = int(round(dataframe['pig_age_days'].quantile(0.65)))
    feeding_count = int(round(dataframe['feeding_count'].median()))
    total_feed_quantity = round(float(dataframe['total_feed_quantity'].median()), 2)

    interval_subset = dataframe[dataframe['feeding_count'] == feeding_count]
    if interval_subset.empty:
        avg_interval = round(float(dataframe['avg_feeding_interval_hours'].median()), 2)
    else:
        avg_interval = round(float(interval_subset['avg_feeding_interval_hours'].median()), 2)

    pen_capacity = int(round(dataframe['pen_capacity'].median()))
    pen_status = str(dataframe['pen_status'].mode().iloc[0])
    window_days = int(dataframe['window_days'].mode().iloc[0])

    return {
        'pig_age_days': age_value,
        'total_feed_quantity': total_feed_quantity,
        'feeding_count': feeding_count,
        'avg_feeding_interval_hours': avg_interval,
        'pen_capacity': pen_capacity,
        'pen_status': pen_status,
        'growth_stage': infer_growth_stage(age_value),
        'window_days': window_days,
    }


def prescriptive_analytics(dataframe, best_model, feature_columns, baseline_sample):
    print_section('PRESCRIPTIVE ANALYTICS')

    target_age = baseline_sample['pig_age_days']
    feed_quantity_range = np.linspace(
        dataframe['total_feed_quantity'].quantile(0.25),
        dataframe['total_feed_quantity'].quantile(0.90),
        8,
    )
    feeding_options = sorted(
        value for value in dataframe['feeding_count'].dropna().astype(int).unique().tolist() if 2 <= value <= 5
    )

    recommendations = []
    for feeding_count in feeding_options:
        interval_subset = dataframe[dataframe['feeding_count'] == feeding_count]
        if interval_subset.empty:
            interval_hours = float(dataframe['avg_feeding_interval_hours'].median())
        else:
            interval_hours = float(interval_subset['avg_feeding_interval_hours'].median())

        for total_feed_quantity in feed_quantity_range:
            candidate = {
                **baseline_sample,
                'pig_age_days': int(target_age),
                'growth_stage': infer_growth_stage(target_age),
                'feeding_count': int(feeding_count),
                'total_feed_quantity': round(float(total_feed_quantity), 2),
                'avg_feeding_interval_hours': round(interval_hours, 2),
            }
            candidate_features = align_feature_matrix(pd.DataFrame([candidate]), feature_columns)
            candidate_prediction = float(best_model.predict(candidate_features)[0])
            recommendations.append({**candidate, 'predicted_avg_weight': candidate_prediction})

    recommendation_frame = pd.DataFrame(recommendations).sort_values(
        'predicted_avg_weight',
        ascending=False,
    )
    best_recommendation = recommendation_frame.iloc[0].to_dict()

    baseline_features = align_feature_matrix(pd.DataFrame([baseline_sample]), feature_columns)
    baseline_prediction = float(best_model.predict(baseline_features)[0])
    expected_gain = best_recommendation['predicted_avg_weight'] - baseline_prediction

    print('Recommended operating point:')
    print(
        json.dumps(
            {
                'target_age_days': int(target_age),
                'target_growth_stage': infer_growth_stage(target_age),
                'recommended_feeding_count': int(best_recommendation['feeding_count']),
                'recommended_total_feed_quantity': round(float(best_recommendation['total_feed_quantity']), 2),
                'recommended_avg_feeding_interval_hours': round(
                    float(best_recommendation['avg_feeding_interval_hours']),
                    2,
                ),
                'predicted_avg_weight': round(float(best_recommendation['predicted_avg_weight']), 2),
                'predicted_weight_gain_vs_baseline': round(float(expected_gain), 2),
            },
            indent=2,
        )
    )

    actions = []
    if best_recommendation['feeding_count'] > baseline_sample['feeding_count']:
        actions.append('Increase feeding frequency for similar pigs to improve predicted growth.')
    elif best_recommendation['feeding_count'] < baseline_sample['feeding_count']:
        actions.append('Reduce feeding frequency slightly and keep intervals more stable to improve efficiency.')
    else:
        actions.append('Maintain the current feeding frequency because it is already near the predicted optimum.')

    if best_recommendation['total_feed_quantity'] > baseline_sample['total_feed_quantity']:
        actions.append('Raise recent total feed quantity in controlled increments while monitoring weight response.')
    elif best_recommendation['total_feed_quantity'] < baseline_sample['total_feed_quantity']:
        actions.append('Avoid overfeeding; similar pigs may perform better with a slightly lower total feed quantity.')
    else:
        actions.append('Keep feed quantity steady and focus on timing consistency.')

    if best_recommendation['pen_status'] == 'occupied':
        actions.append('Closely monitor crowded pens because occupancy can compound feeding and growth issues.')
    else:
        actions.append('Keep pen conditions stable so feeding improvements are easier to validate.')

    actions.append('Prioritize pigs flagged as at risk or below expected weight for additional health and feed-quality checks.')

    print('\nRecommended actions:')
    for action in actions:
        print(f'- {action}')


def parse_prediction_sample(raw_value, dataframe):
    default_sample = build_default_prediction_sample(dataframe)
    if not raw_value:
        return default_sample

    supplied_sample = json.loads(raw_value)
    merged_sample = {**default_sample, **supplied_sample}
    missing_columns = [column for column in MODEL_FEATURE_COLUMNS if column not in merged_sample]
    if missing_columns:
        raise ValueError(f'Prediction sample is missing fields: {missing_columns}')
    return merged_sample


def print_final_summary(regression_result, classification_result, classification_target):
    print_section('FINAL SUMMARY')
    print(f'Best regression model for avg_weight prediction: {regression_result["best_model_name"]}')
    print(f'Best classification model for {classification_target}: {classification_result["best_model_name"]}')

    regression_top = regression_result['results_frame'].iloc[0]
    classification_top = classification_result['results_frame'].iloc[0]
    print('\nTop regression metrics:')
    print(
        json.dumps(
            {
                'r2_score': round(float(regression_top['r2_score']), 4),
                'rmse': round(float(regression_top['rmse']), 4),
                'mae': round(float(regression_top['mae']), 4),
            },
            indent=2,
        )
    )
    print('\nTop classification metrics:')
    print(
        json.dumps(
            {
                'accuracy': round(float(classification_top['accuracy']), 4),
                'precision': round(float(classification_top['precision']), 4),
                'recall': round(float(classification_top['recall']), 4),
                'f1_score': round(float(classification_top['f1_score']), 4),
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description='Analyze SmartHog PigMLData with descriptive, diagnostic, regression, classification, and prescriptive analytics.'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to a PigMLData JSON or CSV file.',
    )
    parser.add_argument(
        '--output-dir',
        default='datamining/analysis_output',
        help='Directory where charts will be saved.',
    )
    parser.add_argument(
        '--prediction-sample',
        help='Optional JSON object containing regression feature values for a future prediction sample.',
    )
    parser.add_argument(
        '--classification-target',
        default='low_growth_risk',
        choices=['low_growth_risk', 'weight_class', 'below_expected_weight_for_age'],
        help='Derived classification target to model.',
    )
    parser.add_argument(
        '--show-plots',
        action='store_true',
        help='Display plots in addition to saving them.',
    )
    args = parser.parse_args()

    dataframe = load_dataset(args.input)
    output_dir = Path(args.output_dir)
    prediction_sample = parse_prediction_sample(args.prediction_sample, dataframe)

    descriptive_analytics(dataframe, output_dir, args.show_plots)
    diagnostic_frame = diagnostic_analytics(dataframe, output_dir, args.show_plots)
    regression_result = regression_analytics_module(
        diagnostic_frame,
        output_dir,
        args.show_plots,
        prediction_sample,
    )
    classification_result = classification_analytics_module(
        diagnostic_frame,
        output_dir,
        args.show_plots,
        args.classification_target,
    )
    prescriptive_analytics(
        diagnostic_frame,
        regression_result['best_model'],
        regression_result['feature_columns'],
        prediction_sample,
    )
    print_final_summary(regression_result, classification_result, args.classification_target)

    print_section('OUTPUT FILES')
    print(f'Charts saved to: {output_dir.resolve()}')


if __name__ == '__main__':
    main()
