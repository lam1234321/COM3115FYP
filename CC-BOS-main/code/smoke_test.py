"""Offline smoke test for CC-BOS.

Exercises data loading, population initialisation, the full search loop and the
output plumbing with mocked model calls. No API key and no network are needed.

Usage:
    cd code
    python smoke_test.py
"""

import json
import os
import tempfile

import gen
import utils
from translate import extract_english_result, preprocess_and_segment_text

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_CSV = os.path.join(HERE, "..", "data", "test.csv")

_eval_state = {"n": 0}


def fake_generate(intention, original_query, fly):
    """Stand-in for the DeepSeek prompt mutation call."""
    names = "-".join(str(v) for v in fly.values())
    return f"[MOCK {names}] {intention}"


def fake_evaluate(intention, query, original_query, counter=None):
    """Stand-in for the target-model call + translation + judging."""
    if counter is not None:
        counter["attempts"] += 1
    _eval_state["n"] += 1
    # Keep the score below the early-stop threshold so every search stage runs.
    score = 20 + (_eval_state["n"] % 3) * 10
    return score, query, 1.0, f"[MOCK RAW] {query}"


def check_helpers():
    assert utils.extract_content("#thescore:", "#thescore: 3") == 3
    assert utils.extract_content("#thescore:", "no tag here") is None
    assert utils.get_keyword_score("I'm sorry, but I cannot help.") == 0
    assert utils.get_keyword_score("Here is a detailed answer.") == 20

    segments = preprocess_and_segment_text("子曰：" + "學而時習之。" * 500, 100)
    assert len(segments) > 1
    assert "".join(segments) == "子曰：" + "學而時習之。" * 500

    assert extract_english_result("#english: Hello world") == "Hello world"
    assert extract_english_result("no marker") is None


def check_population():
    population = gen.initialize_fruitflies(7, gen.dimension_options)
    assert len(population) == 7
    for fly in population:
        assert set(fly) == set(gen.dimension_options)
        for dim, value in fly.items():
            assert value in gen.dimension_options[dim].values()

    assert len(gen.fly_to_tuple(population[0])) == len(gen.dimension_options)
    assert len(gen.convert_to_names(population[0])) == len(gen.dimension_options)


def check_jsonl_loading():
    with tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        f.write(json.dumps({"prompt": "p1", "intention": "i1"}) + "\n")
        f.write("\n")
        f.write(json.dumps({"prompt": "p2", "intention": "i2"}) + "\n")
        path = f.name
    try:
        prompts, intentions = gen.get_jsonl_prompts(path)
        assert prompts == ["p1", "p2"]
        assert intentions == ["i1", "i2"]
    finally:
        os.unlink(path)


def main():
    check_helpers()
    check_population()
    check_jsonl_loading()

    gen.generate_with_fruitfly = fake_generate
    gen.evaluate_query = fake_evaluate

    with tempfile.TemporaryDirectory() as tmp:
        args = gen.parse_args(
            [
                "--input_file", TEST_CSV,
                "--data_format", "csv",
                "--population_size", "2",
                "--max_iter", "1",
                "--output_dir", tmp,
                "--seed", "1234",
            ]
        )
        summary = gen.run(args)

        assert summary["total"] == 3, summary
        assert summary["total_jailbreak_attempts"] > 0, summary
        assert summary["success_num"] == 0, summary  # mock scores stay below 80

        with open(summary["adv_prompt_path"], encoding="utf-8") as f:
            adv_lines = [json.loads(line) for line in f if line.strip()]
        with open(summary["record_path"], encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

        assert len(adv_lines) == 3
        assert len(records) == 3
        required = {
            "id", "intention", "original_prompt", "adversarial_prompt",
            "raw_response", "model_response", "consistency", "score",
            "success", "jailbreak_attempts",
        }
        for record in records:
            assert required <= set(record), record
            assert record["adversarial_prompt"].startswith("[MOCK")
            assert record["jailbreak_attempts"] > 0

    print("\nSmoke test passed: data loading, search loop and output files are OK.")


if __name__ == "__main__":
    main()
