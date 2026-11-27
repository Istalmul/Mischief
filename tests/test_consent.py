import pytest

from mischief.consent import ConsentError, require_allowed, split_voices, voice_from_profile


def test_only_verified_clones_and_designed_voices_are_allowed(profiles):
    allowed, blocked = split_voices(profiles)
    assert [v.id for v in allowed] == ["me", "robot"]
    assert [v.id for v in blocked] == ["celeb", "legacy"]


def test_null_kind_is_treated_as_clone(profiles):
    assert voice_from_profile(profiles[3]).kind == "clone"


def test_require_allowed_blocks_unverified_clone(profiles):
    with pytest.raises(ConsentError):
        require_allowed(voice_from_profile(profiles[2]))
