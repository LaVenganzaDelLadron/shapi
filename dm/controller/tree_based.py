from collections import Counter
from typing import Any, Dict, List, Tuple
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from record.models import Record


def load_training_dataset() -> Tuple[List[List[float]], List[str]]:
    """
    Build feature matrix X and target vector y from Record rows.

    Features:
    - pig_age_days
    - avg_weight

    Target:
    - growth_stage.growth_code
    """
    rows = list(
        Record.objects.select_related("growth_stage")
        .order_by("record_code")
        .values_list("pig_age_days", "avg_weight", "growth_stage__growth_code")
    )

    if not rows:
        raise ValueError("No records found. Create record data before training.")

    x_data = [[float(age_days), float(avg_weight)] for age_days, avg_weight, _ in rows]
    y_data = [str(growth_code) for _, _, growth_code in rows]
    return x_data, y_data


def train_decision_tree_from_database(
    test_size: float = 0.2,
    random_state: int = 42,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
) -> Dict[str, Any]:
    """
    Train and evaluate a Decision Tree model using database data.

    Returns:
        dict containing model, label_encoder, feature names, class names and metrics.
    """
    x_data, y_data = load_training_dataset()

    class_count = len(set(y_data))
    if class_count < 2:
        raise ValueError("Need at least 2 growth stages to train a classifier.")

    if len(y_data) < 4:
        raise ValueError("Need at least 4 records to split train/test reliably.")

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y_data)

    # Stratify only if every class has at least 2 samples.
    label_frequencies = Counter(y_encoded)
    stratify_target = y_encoded if min(label_frequencies.values()) >= 2 else None

    x_train, x_test, y_train, y_test = train_test_split(
        x_data,
        y_encoded,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_target,
    )

    classifier = DecisionTreeClassifier(
        random_state=random_state,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
    )
    classifier.fit(x_train, y_train)

    y_pred = classifier.predict(x_test)
    accuracy = float(accuracy_score(y_test, y_pred))

    return {
        "model": classifier,
        "label_encoder": label_encoder,
        "feature_names": ["pig_age_days", "avg_weight"],
        "class_names": label_encoder.classes_.tolist(),
        "metrics": {
            "accuracy": accuracy,
            "train_size": len(x_train),
            "test_size": len(x_test),
            "total_records": len(x_data),
            "tree_depth": classifier.get_depth(),
            "leaf_count": classifier.get_n_leaves(),
        },
    }


def predict_growth_stage(
    model: DecisionTreeClassifier,
    label_encoder: LabelEncoder,
    pig_age_days: float,
    avg_weight: float,
) -> str:
    """
    Predict growth stage code for one sample.
    """
    encoded = model.predict([[float(pig_age_days), float(avg_weight)]])[0]
    return str(label_encoder.inverse_transform([encoded])[0])



