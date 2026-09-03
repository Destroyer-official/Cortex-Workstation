"""Tests for the offline Smart Suggestions learning engine.

Verifies it actually learns (predictions move in the right direction after
feedback), stays bounded in size, persists locally, and never crashes on bad
input - all with zero network access.
"""

from __future__ import annotations

from cortex_unified.core.smart_suggest import SmartSuggester, featurize


def _ctx(category="user_temp", ext="tmp", size=5_000_000, age=40, path="C:/Users/x/AppData/Local/Temp/f.tmp"):
    """_ctx."""
    return {"category": category, "extension": ext, "size": size, "age_days": age, "path": path}


class TestFeaturize:
    """TestFeaturize."""
    def test_includes_bias_and_known_features(self):
        """test_includes_bias_and_known_features."""
        feats = featurize(_ctx())
        assert "bias" in feats
        assert "cat:user_temp" in feats
        assert "ext:tmp" in feats
        assert any(f.startswith("sz:") for f in feats)
        assert any(f.startswith("age:") for f in feats)
        assert "loc:temp" in feats or "loc:appdata" in feats

    def test_handles_sparse_context(self):
        """test_handles_sparse_context."""
        assert featurize({}) == ["bias"]
        assert "cat:cache" in featurize({"category": "Cache"})


class TestLearning:
    """TestLearning."""
    def test_score_in_unit_interval(self, tmp_path):
        """test_score_in_unit_interval."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        assert 0.0 <= s.score(_ctx()) <= 1.0

    def test_learns_to_favor_accepted_pattern(self, tmp_path):
        """test_learns_to_favor_accepted_pattern."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        ctx = _ctx()
        before = s.score(ctx)
        # User repeatedly cleans this kind of item -> score should rise.
        for _ in range(40):
            s.observe(ctx, cleaned=True)
        after = s.score(ctx)
        assert after > before
        assert after > 0.7

    def test_learns_to_avoid_skipped_pattern(self, tmp_path):
        """test_learns_to_avoid_skipped_pattern."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        ctx = _ctx(category="documents", ext="docx", path="C:/Users/x/Documents/report.docx")
        for _ in range(40):
            s.observe(ctx, cleaned=False)
        assert s.score(ctx) < 0.3

    def test_recommend_defaults_true_until_trained(self, tmp_path):
        """test_recommend_defaults_true_until_trained."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        # Fewer than 10 updates -> don't second-guess the user.
        assert s.recommend(_ctx()) is True

    def test_rank_orders_by_score(self, tmp_path):
        """test_rank_orders_by_score."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        good = _ctx(category="user_temp")
        bad = _ctx(category="documents", ext="docx", path="C:/Users/x/Documents/a.docx")
        for _ in range(30):
            s.observe(good, cleaned=True)
            s.observe(bad, cleaned=False)
        ranked = s.rank([bad, good])
        assert ranked[0][0]["category"] == "user_temp"  # higher score first


class TestBoundsAndPersistence:
    """TestBoundsAndPersistence."""
    def test_model_size_is_capped(self, tmp_path):
        """test_model_size_is_capped."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        # Feed many distinct extensions to blow past the cap, ensure it's bounded.
        from cortex_unified.core import smart_suggest
        for i in range(smart_suggest._MAX_FEATURES + 500):
            s.observe({"category": f"c{i}", "extension": f"e{i}"}, cleaned=bool(i % 2))
        assert s.stats()["feature_count"] <= smart_suggest._MAX_FEATURES

    def test_save_and_reload_roundtrip(self, tmp_path):
        """test_save_and_reload_roundtrip."""
        path = tmp_path / "m.json"
        s = SmartSuggester(model_path=path)
        for _ in range(20):
            s.observe(_ctx(), cleaned=True)
        trained_score = s.score(_ctx())
        assert s.save() is True
        assert path.exists()

        s2 = SmartSuggester(model_path=path)          # reload
        assert abs(s2.score(_ctx()) - trained_score) < 1e-9
        assert s2.stats()["updates"] == 20

    def test_corrupt_model_does_not_crash(self, tmp_path):
        """test_corrupt_model_does_not_crash."""
        path = tmp_path / "m.json"
        path.write_text("{ this is not valid json", encoding="utf-8")
        s = SmartSuggester(model_path=path)            # must not raise
        assert s.stats()["updates"] == 0

    def test_reset(self, tmp_path):
        """test_reset."""
        s = SmartSuggester(model_path=tmp_path / "m.json")
        for _ in range(15):
            s.observe(_ctx(), cleaned=True)
        s.reset()
        assert s.stats()["updates"] == 0
        assert s.stats()["feature_count"] == 0
