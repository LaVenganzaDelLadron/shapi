import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
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

FEATURE_COLUMNS = [
    'pig_age_days',
    'feeding_count',
    'total_feed_quantity',
    'avg_feeding_interval_hours',
]

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

    return dataframe


def build_models(dataframe):
    dataset = dataframe.dropna(subset=FEATURE_COLUMNS + ['avg_weight']).copy()
    if len(dataset) < 10:
        raise ValueError('At least 10 clean rows are needed for model training.')

    features = dataset[FEATURE_COLUMNS]
    target = dataset['avg_weight']

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
    )

    models = {
        'Linear Regression': Pipeline(
            [
                ('scaler', StandardScaler()),
                ('model', LinearRegression()),
            ]
        ),
        'Decision Tree': DecisionTreeRegressor(
            random_state=42,
            max_depth=5,
            min_samples_leaf=3,
        ),
        'Random Forest': RandomForestRegressor(
            random_state=42,
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            n_jobs=-1,
        ),
    }

    results = []
    trained_models = {}
    predictions = {}

    for model_name, model in models.items():
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, predicted)))
        score = r2_score(y_test, predicted)
        results.append({'model': model_name, 'r2_score': score, 'rmse': rmse})
        trained_models[model_name] = model
        predictions[model_name] = predicted

    results_frame = pd.DataFrame(results).sort_values('r2_score', ascending=False).reset_index(drop=True)
    best_model_name = results_frame.iloc[0]['model']
    best_model = trained_models[best_model_name]

    best_model.fit(features, target)

    return {
        'results_frame': results_frame,
        'best_model_name': best_model_name,
        'best_model': best_model,
        'x_test': x_test,
        'y_test': y_test,
        'test_predictions': predictions[best_model_name],
    }


def extract_feature_importance(best_model):
    if isinstance(best_model, Pipeline):
        final_model = best_model.named_steps['model']
        if hasattr(final_model, 'coef_'):
            return pd.Series(np.abs(final_model.coef_), index=FEATURE_COLUMNS).sort_values(ascending=False)
        if hasattr(final_model, 'feature_importances_'):
            return pd.Series(final_model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
        return None

    if hasattr(best_model, 'feature_importances_'):
        return pd.Series(best_model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    if hasattr(best_model, 'coef_'):
        return pd.Series(np.abs(best_model.coef_), index=FEATURE_COLUMNS).sort_values(ascending=False)
    return None


def predictive_analytics(dataframe, output_dir, show_plots, prediction_sample):
    print_section('PREDICTIVE ANALYTICS')
    model_bundle = build_models(dataframe)
    results_frame = model_bundle['results_frame']
    best_model_name = model_bundle['best_model_name']
    best_model = model_bundle['best_model']

    print('Model comparison:')
    print(results_frame.round(4).to_string(index=False))
    print(f'\nBest model selected: {best_model_name}')

    sample_frame = pd.DataFrame([prediction_sample], columns=FEATURE_COLUMNS)
    predicted_weight = float(best_model.predict(sample_frame)[0])
    print('\nFuture weight prediction for sample input:')
    print(json.dumps({**prediction_sample, 'predicted_avg_weight': round(predicted_weight, 2)}, indent=2))

    importance = extract_feature_importance(best_model)
    if importance is not None:
        print('\nFeature importance:')
        print(importance.round(4).to_string())

        plt.figure(figsize=(8, 5))
        importance.sort_values().plot(kind='barh', color='#4C956C')
        plt.title(f'Feature Importance - {best_model_name}')
        plt.xlabel('Importance Score')
        save_plot(output_dir, 'predictive_feature_importance.png', show_plots)

    plt.figure(figsize=(7, 6))
    plt.scatter(
        model_bundle['y_test'],
        model_bundle['test_predictions'],
        color='#2C7DA0',
        alpha=0.7,
        edgecolors='black',
        linewidths=0.3,
    )
    min_value = min(model_bundle['y_test'].min(), model_bundle['test_predictions'].min())
    max_value = max(model_bundle['y_test'].max(), model_bundle['test_predictions'].max())
    plt.plot([min_value, max_value], [min_value, max_value], color='#D1495B', linestyle='--')
    plt.title(f'Actual vs Predicted Weight ({best_model_name})')
    plt.xlabel('Actual Weight (kg)')
    plt.ylabel('Predicted Weight (kg)')
    save_plot(output_dir, 'predictive_actual_vs_predicted.png', show_plots)

    return {
        'best_model': best_model,
        'best_model_name': best_model_name,
        'predicted_weight': predicted_weight,
        'feature_importance': importance,
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

    return {
        'pig_age_days': age_value,
        'feeding_count': feeding_count,
        'total_feed_quantity': total_feed_quantity,
        'avg_feeding_interval_hours': avg_interval,
    }


def prescriptive_analytics(dataframe, best_model, baseline_sample):
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
                'pig_age_days': target_age,
                'feeding_count': int(feeding_count),
                'total_feed_quantity': round(float(total_feed_quantity), 2),
                'avg_feeding_interval_hours': round(interval_hours, 2),
            }
            candidate_prediction = float(best_model.predict(pd.DataFrame([candidate]))[0])
            recommendations.append({**candidate, 'predicted_avg_weight': candidate_prediction})

    recommendation_frame = pd.DataFrame(recommendations).sort_values(
        'predicted_avg_weight',
        ascending=False,
    )
    best_recommendation = recommendation_frame.iloc[0].to_dict()

    baseline_prediction = float(best_model.predict(pd.DataFrame([baseline_sample]))[0])
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

    actions.append('Prioritize pens or batches flagged as anomalies for health, feed quality, and stress checks.')
    actions.append('Rebuild the PigMLData dataset regularly so recommendations stay aligned with recent farm behavior.')

    print('\nRecommended actions:')
    for action in actions:
        print(f'- {action}')


def parse_prediction_sample(raw_value, dataframe):
    if not raw_value:
        return build_default_prediction_sample(dataframe)

    sample = json.loads(raw_value)
    missing_columns = [column for column in FEATURE_COLUMNS if column not in sample]
    if missing_columns:
        raise ValueError(f'Prediction sample is missing fields: {missing_columns}')
    return sample


def main():
    parser = argparse.ArgumentParser(description='Analyze SmartHog PigMLData with descriptive, diagnostic, predictive, and prescriptive analytics.')
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
        help='Optional JSON object with pig_age_days, feeding_count, total_feed_quantity, and avg_feeding_interval_hours.',
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
    predictive_result = predictive_analytics(
        diagnostic_frame,
        output_dir,
        args.show_plots,
        prediction_sample,
    )
    prescriptive_analytics(
        diagnostic_frame,
        predictive_result['best_model'],
        prediction_sample,
    )

    print_section('OUTPUT FILES')
    print(f'Charts saved to: {output_dir.resolve()}')


if __name__ == '__main__':
    main()
