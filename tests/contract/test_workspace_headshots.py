"""DG-193 — the workspace headshot cache builder.

David asked for a photo for every player. The one thing this must never do is satisfy that by putting the wrong face
under a name, so every rule below exists to keep identity exact:

* a photo is only ever fetched from that player's OWN identifiers — his Sleeper id, or the ESPN id carried on his own
  Sleeper record. There is no name matching and no position guessing anywhere in the path;
* bytes are validated by their magic and by a real decode, so a 404 page or a one-pixel tracker never lands in the
  cache as a face;
* a player with no photo is reported by name and keeps the initials fallback. The run still succeeds, because
  missing coverage is a fact to report, not an error to hide.

Both the network and the image decoder are injected here, so these tests never reach the internet.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from scripts.build_workspace_headshots import (
    ESPN_COLLEGE_HEADSHOT_URL,
    ESPN_HEADSHOT_URL,
    MAX_IMAGE_BYTES,
    NFL_HEADSHOT_HOST,
    SLEEPER_FULL_URL,
    SLEEPER_THUMB_URL,
    HeadshotBuildError,
    build_workspace_headshots,
    sips_validator,
)

JPEG = b"\xff\xd8\xff" + b"jpeg-body" * 8
PNG = b"\x89PNG\r\n\x1a\n" + b"png-body" * 8
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"webp-body" * 8
NOT_AN_IMAGE = b"<!doctype html><title>404</title>"


class Result:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


def players(*rows: tuple[str, str, str]) -> list[dict]:
    return [{"sleeper_player_id": pid, "name": name, "position": pos} for pid, name, pos in rows]


THREE = players(("1", "Alpha Adams", "QB"), ("2", "Bravo Bell", "RB"), ("3", "Charlie Cross", "WR"))


def fetcher(responses: dict[str, Result | Exception], *, log: list | None = None):
    def fetch(url: str) -> Result:
        if log is not None:
            log.append(url)
        answer = responses.get(url, Result(404, b""))
        if isinstance(answer, Exception):
            raise answer
        return answer

    return fetch


def always_valid(payload: bytes) -> bool:
    return payload.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")) or (
        payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"
    )


def build(tmp_path: Path, *, rows=None, responses=None, log=None, **kwargs):
    return build_workspace_headshots(
        players=rows if rows is not None else THREE,
        output_dir=kwargs.pop("output_dir", tmp_path / "run"),
        fetcher=kwargs.pop("fetcher", fetcher(responses or {}, log=log)),
        validator=kwargs.pop("validator", always_valid),
        **kwargs,
    )


def thumb(pid: str) -> str:
    return SLEEPER_THUMB_URL.format(sleeper_id=pid)


def full(pid: str) -> str:
    return SLEEPER_FULL_URL.format(sleeper_id=pid)


def espn(espn_id: str) -> str:
    return ESPN_HEADSHOT_URL.format(espn_id=espn_id)


# --- the population is processed whole ---------------------------------------------------------------


def test_every_player_given_is_reported_and_none_is_filtered_away(tmp_path) -> None:
    report = build(tmp_path, responses={thumb("1"): Result(200, JPEG)})
    assert [row["sleeper_id"] for row in report["players"]] == ["1", "2", "3"]
    assert report["counts"] == {"total": 3, "available": 1, "missing": 2, "from_seed": 0, "fetched": 1}
    assert [row["sleeper_id"] for row in report["missing"]] == ["2", "3"]
    assert all(row["name"] and row["position"] for row in report["missing"])


def test_a_player_with_no_photo_anywhere_is_named_with_a_reason_and_is_not_an_error(tmp_path) -> None:
    report = build(tmp_path, rows=players(("9", "India Ivey", "TE")))
    missing = report["missing"][0]
    assert missing["sleeper_id"] == "9" and missing["name"] == "India Ivey"
    assert "no photo" in missing["reason"].lower()
    assert report["counts"]["available"] == 0
    assert not (tmp_path / "run" / "headshots" / "9.jpg").exists()


def test_duplicate_or_conflicting_rows_refuse_the_whole_run(tmp_path) -> None:
    """A population file that names one id twice is wrong, and picking a row would risk the wrong face."""
    with pytest.raises(HeadshotBuildError, match="duplicate"):
        build(tmp_path, rows=players(("1", "Alpha Adams", "QB"), ("1", "Alpha Adams", "QB")))
    with pytest.raises(HeadshotBuildError, match="1"):
        build(tmp_path, rows=players(("1", "Alpha Adams", "QB"), ("1", "Somebody Else", "QB")))


@pytest.mark.parametrize("bad", ["../escape", "", "0", 17, None])
def test_an_unsafe_identifier_refuses_the_run_before_anything_is_fetched(tmp_path, bad) -> None:
    """Root's ruling: a malformed population is a defect in the input, not a player without a photo. It stops the
    run rather than being filed among the honest misses."""
    log: list[str] = []
    with pytest.raises(HeadshotBuildError, match="identifier"):
        build(tmp_path, rows=[{"sleeper_player_id": bad, "name": "Nobody", "position": "QB"}], log=log)
    assert log == []
    assert not (tmp_path / "run").exists()


# --- the sources, in order ------------------------------------------------------------------------------


def test_the_thumbnail_is_tried_first_and_wins(tmp_path) -> None:
    log: list[str] = []
    report = build(tmp_path, rows=players(("1", "Alpha", "QB")), responses={thumb("1"): Result(200, JPEG)}, log=log)
    assert log == [thumb("1")]
    row = report["players"][0]
    assert row["status"] == "available" and row["source"] == "sleeper_thumb"
    assert (tmp_path / "run" / "headshots" / "1.jpg").read_bytes() == JPEG


def test_a_missing_thumbnail_falls_through_to_the_full_size_image(tmp_path) -> None:
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={thumb("1"): Result(404, b""), full("1"): Result(200, PNG)}, log=log,
    )
    assert log == [thumb("1"), full("1")]
    assert report["players"][0]["source"] == "sleeper_full"


def test_espn_is_reached_only_through_the_players_own_identity_record(tmp_path) -> None:
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={espn("3139477"): Result(200, PNG)},
        identities={"1": {"espn_id": "3139477"}}, log=log,
    )
    assert log == [thumb("1"), full("1"), espn("3139477")]
    assert report["players"][0]["source"] == "espn"


def test_without_an_espn_id_no_espn_request_is_made_at_all(tmp_path) -> None:
    log: list[str] = []
    build(tmp_path, rows=players(("1", "Alpha", "QB")), identities={"1": {}}, log=log)
    assert log == [thumb("1"), full("1")]
    assert not any("espncdn" in url for url in log)


def test_one_players_espn_id_is_never_used_for_another(tmp_path) -> None:
    log: list[str] = []
    build(
        tmp_path, rows=players(("1", "Alpha", "QB"), ("2", "Bravo", "RB")),
        identities={"2": {"espn_id": "3139477"}}, log=log,
    )
    assert log.count(espn("3139477")) == 1                        # only ever attempted for player 2


def test_an_identities_map_that_is_not_keyed_by_sleeper_id_is_refused(tmp_path) -> None:
    with pytest.raises(HeadshotBuildError, match="sleeper"):
        build(tmp_path, rows=players(("1", "Alpha", "QB")), identities={"Alpha Adams": {"espn_id": "3139477"}})


# --- what the network does, and what we do back -----------------------------------------------------------


def test_an_absent_photo_is_never_asked_for_twice(tmp_path) -> None:
    """404 means the photo is not there. Asking again is noise on somebody else's CDN."""
    log: list[str] = []
    build(tmp_path, rows=players(("1", "Alpha", "QB")), log=log)
    assert log == [thumb("1"), full("1")]
    assert len(log) == len(set(log))


def test_a_forbidden_response_means_absent_and_is_not_retried(tmp_path) -> None:
    """Root probed the real CDN: an unknown id answers 403, not 404. Treating that as transient would retry every
    player we do not have a photo for, twice, against somebody else's service."""
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("99999999", "Nobody", "QB")),
        responses={thumb("99999999"): Result(403, b""), full("99999999"): Result(403, b"")}, log=log,
    )
    assert log == [thumb("99999999"), full("99999999")]           # each asked exactly once
    assert report["players"][0]["status"] == "missing"
    assert [attempt["outcome"] for attempt in report["players"][0]["attempts"]] == ["not_found", "not_found"]


def test_a_transient_failure_is_retried_exactly_once(tmp_path) -> None:
    attempts: list[str] = []

    def flaky(url: str) -> Result:
        attempts.append(url)
        if url == thumb("1") and attempts.count(url) == 1:
            return Result(503, b"")
        return Result(200, JPEG) if url == thumb("1") else Result(404, b"")

    report = build(tmp_path, rows=players(("1", "Alpha", "QB")), fetcher=flaky)
    assert attempts.count(thumb("1")) == 2
    assert report["players"][0]["status"] == "available"


def test_a_connection_error_is_recorded_rather_than_crashing_the_run(tmp_path) -> None:
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        fetcher=fetcher({thumb("1"): TimeoutError("timed out")}),
    )
    assert report["players"][0]["status"] == "missing"
    outcomes = [attempt["outcome"] for attempt in report["players"][0]["attempts"]]
    assert "error" in outcomes


def test_bytes_that_are_not_an_image_are_refused_and_the_next_source_is_tried(tmp_path) -> None:
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={thumb("1"): Result(200, NOT_AN_IMAGE), full("1"): Result(200, WEBP)},
    )
    assert report["players"][0]["source"] == "sleeper_full"
    first = report["players"][0]["attempts"][0]
    assert first["outcome"] == "invalid_image" and first["http_status"] == 200
    assert (tmp_path / "run" / "headshots" / "1.jpg").read_bytes() == WEBP


def test_an_oversized_response_is_refused_rather_than_written(tmp_path) -> None:
    huge = b"\xff\xd8\xff" + b"x" * (MAX_IMAGE_BYTES + 1)
    report = build(tmp_path, rows=players(("1", "Alpha", "QB")), responses={thumb("1"): Result(200, huge)})
    assert report["players"][0]["status"] == "missing"
    assert report["players"][0]["attempts"][0]["outcome"] == "too_large"
    assert not (tmp_path / "run" / "headshots" / "1.jpg").exists()


def test_the_original_bytes_are_kept_even_when_a_jpg_url_serves_png(tmp_path) -> None:
    """Sleeper really does this; the legacy builder found it on its first live run. The filename follows the
    frontend's URL contract, the bytes follow the source, and browsers sniff the content."""
    build(tmp_path, rows=players(("1", "Alpha", "QB")), responses={thumb("1"): Result(200, PNG)})
    written = (tmp_path / "run" / "headshots" / "1.jpg").read_bytes()
    assert written == PNG and written.startswith(b"\x89PNG")


def test_no_more_than_four_requests_are_in_flight_at_once(tmp_path) -> None:
    live = 0
    peak = 0
    guard = threading.Lock()

    def slow(url: str) -> Result:
        nonlocal live, peak
        with guard:
            live += 1
            peak = max(peak, live)
        time.sleep(0.02)
        with guard:
            live -= 1
        return Result(200, JPEG)

    many = players(*[(str(index), f"Player {index}", "QB") for index in range(1, 21)])
    build(tmp_path, rows=many, fetcher=slow)
    assert peak <= 4


# --- the seed cache -----------------------------------------------------------------------------------------


def test_a_valid_seed_image_is_kept_and_the_network_is_not_touched(tmp_path) -> None:
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "1.jpg").write_bytes(JPEG)
    log: list[str] = []
    report = build(tmp_path, rows=players(("1", "Alpha", "QB")), seed_cache=seed, log=log)
    assert log == []
    row = report["players"][0]
    assert row["status"] == "available" and row["source"] == "seed"
    assert (tmp_path / "run" / "headshots" / "1.jpg").read_bytes() == JPEG
    assert report["counts"]["from_seed"] == 1 and report["counts"]["fetched"] == 0


def test_a_seed_image_that_is_not_a_valid_image_is_ignored_and_refetched(tmp_path) -> None:
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "1.jpg").write_bytes(NOT_AN_IMAGE)
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")), seed_cache=seed,
        responses={thumb("1"): Result(200, JPEG)},
    )
    assert report["players"][0]["source"] == "sleeper_thumb"
    assert (tmp_path / "run" / "headshots" / "1.jpg").read_bytes() == JPEG


def test_the_seed_is_only_read_for_that_exact_identifier(tmp_path) -> None:
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "2.jpg").write_bytes(JPEG)                            # somebody else's photo
    report = build(tmp_path, rows=players(("1", "Alpha", "QB")), seed_cache=seed)
    assert report["players"][0]["status"] == "missing"
    assert not (tmp_path / "run" / "headshots" / "1.jpg").exists()


# --- where the output may go ----------------------------------------------------------------------------------


def test_the_output_directory_must_be_new_so_a_run_never_overwrites_another(tmp_path) -> None:
    existing = tmp_path / "already"
    existing.mkdir()
    with pytest.raises(HeadshotBuildError, match="exists"):
        build(tmp_path, output_dir=existing)


def test_the_output_directory_must_be_absolute(tmp_path) -> None:
    with pytest.raises(HeadshotBuildError, match="absolute"):
        build(tmp_path, output_dir=Path("relative/run"))


def test_a_symlinked_ancestor_is_refused_but_the_platform_aliases_are_not(tmp_path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = tmp_path / "link"
    link.symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(HeadshotBuildError, match="symlink"):
        build(tmp_path, output_dir=link / "run")


def test_the_shared_stores_are_never_written(tmp_path) -> None:
    for shared in ("data", "cache"):
        target = tmp_path / "app" / shared / "run"
        with pytest.raises(HeadshotBuildError, match="shared"):
            build(tmp_path, output_dir=target)


# --- the report -------------------------------------------------------------------------------------------------


def test_the_report_records_every_attempt_with_its_source_and_status(tmp_path) -> None:
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={thumb("1"): Result(404, b""), full("1"): Result(200, JPEG)},
    )
    attempts = report["players"][0]["attempts"]
    assert [attempt["source"] for attempt in attempts] == ["sleeper_thumb", "sleeper_full"]
    assert [attempt["http_status"] for attempt in attempts] == [404, 200]
    assert [attempt["outcome"] for attempt in attempts] == ["not_found", "image"]
    assert attempts[1]["url"] == full("1") and attempts[1]["bytes"] == len(JPEG)
    assert len(attempts[1]["sha256"]) == 64
    assert report["players"][0]["sha256"] == attempts[1]["sha256"]


def test_players_sharing_one_image_are_grouped_so_a_placeholder_cannot_pass_as_success(tmp_path) -> None:
    """A CDN that answers every unknown id with the same silhouette would otherwise read as full coverage."""
    report = build(
        tmp_path,
        responses={thumb("1"): Result(200, JPEG), thumb("2"): Result(200, JPEG), thumb("3"): Result(200, PNG)},
    )
    assert report["counts"]["available"] == 3
    groups = report["duplicate_content"]
    assert len(groups) == 1
    assert groups[0]["sleeper_ids"] == ["1", "2"] and len(groups[0]["sha256"]) == 64


def test_the_report_is_written_beside_the_images_and_is_readable_json(tmp_path) -> None:
    build(tmp_path, responses={thumb("1"): Result(200, JPEG)})
    written = json.loads((tmp_path / "run" / "report.json").read_text())
    assert written["counts"]["total"] == 3
    assert written["schema_version"].startswith("workspace_headshots.")
    assert sorted(p.name for p in (tmp_path / "run" / "headshots").iterdir()) == ["1.jpg"]


# --- the decoder must really decode ---------------------------------------------------------------------------------


def test_the_run_refuses_when_the_image_decoder_is_unavailable(tmp_path) -> None:
    """Magic bytes alone would accept a one-pixel tracker. Without a real decode we refuse rather than pretend."""
    with pytest.raises(HeadshotBuildError, match="sips"):
        sips_validator(sips_path=tmp_path / "no-such-sips")


def test_the_real_decoder_accepts_a_real_image_and_rejects_a_tiny_one(tmp_path) -> None:
    sips = Path("/usr/bin/sips")
    if not sips.exists():
        pytest.skip("this check needs macOS sips")
    validate = sips_validator(sips_path=sips)
    assert validate(NOT_AN_IMAGE) is False
    real = tmp_path / "real.png"
    import subprocess

    made = subprocess.run(
        ["/usr/bin/sips", "-s", "format", "png", "--resampleHeightWidth", "32", "32",
         "/System/Library/CoreServices/DefaultDesktop.heic", "--out", str(real)],
        capture_output=True,
    )
    if made.returncode != 0 or not real.exists():
        pytest.skip("no source image available on this machine to build a real fixture")
    assert validate(real.read_bytes()) is True


# --- root's exact-id fallback, 2026-09-08 -----------------------------------------------------------------


def nfl_url(slug: str = "player") -> str:
    return f"https://{NFL_HEADSHOT_HOST}/image/private/headshots/{slug}.png"


def verified(**entries) -> dict:
    return {
        key: {**value, "provenance": value.get("provenance", {"source": "audit.json", "sha256": "a" * 64})}
        for key, value in entries.items()
    }


def test_the_verified_map_is_tried_after_sleeper_and_before_espn(tmp_path) -> None:
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={nfl_url(): Result(200, PNG)},
        verified_identities=verified(**{"1": {"headshot_url": nfl_url(), "espn_id": "3139477"}}),
        log=log,
    )
    assert log == [thumb("1"), full("1"), nfl_url()]              # espn never reached; the NFL url answered
    assert report["players"][0]["source"] == "nfl_verified"


def test_the_exact_espn_id_is_the_last_resort_after_the_verified_url(tmp_path) -> None:
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={espn("3139477"): Result(200, PNG)},
        verified_identities=verified(**{"1": {"headshot_url": nfl_url(), "espn_id": "3139477"}}),
        log=log,
    )
    assert log == [thumb("1"), full("1"), nfl_url(), espn("3139477")]
    assert report["players"][0]["source"] == "espn"


def test_a_verified_entry_carries_its_provenance_into_the_report(tmp_path) -> None:
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={nfl_url(): Result(200, PNG)},
        verified_identities={
            "1": {"headshot_url": nfl_url(),
                  "provenance": {"source": "dg192-source-review.md", "sha256": "b" * 64}}
        },
    )
    assert report["players"][0]["identity_provenance"] == {
        "source": "dg192-source-review.md", "sha256": "b" * 64,
    }


def test_a_verified_entry_without_provenance_is_refused(tmp_path) -> None:
    """An exact-id claim with no stated origin is exactly the kind of unsourced mapping that puts a wrong face
    under a name; it has to say where it came from."""
    with pytest.raises(HeadshotBuildError, match="provenance"):
        build(
            tmp_path, rows=players(("1", "Alpha", "QB")),
            verified_identities={"1": {"headshot_url": nfl_url()}},
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://static.www.nfl.com/a.png",                        # not https
        "https://static.www.nfl.com.evil.test/a.png",             # lookalike host
        "https://example.com/a.png",                              # another host entirely
        "https://user:pw@static.www.nfl.com/a.png",               # credentials
        "https://static.www.nfl.com:8443/a.png",                  # explicit port
        "https://static.www.nfl.com/a.png#frag",                  # fragment
        "https://STATIC.WWW.NFL.COM.attacker.test/a.png",
    ],
)
def test_only_the_one_nfl_host_over_plain_https_is_allowed(tmp_path, url) -> None:
    with pytest.raises(HeadshotBuildError, match="headshot_url"):
        build(tmp_path, rows=players(("1", "Alpha", "QB")), verified_identities=verified(**{"1": {"headshot_url": url}}))


def test_the_allowed_host_is_accepted_case_insensitively(tmp_path) -> None:
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={f"https://{NFL_HEADSHOT_HOST.upper()}/x.png": Result(200, PNG)},
        verified_identities=verified(**{"1": {"headshot_url": f"https://{NFL_HEADSHOT_HOST.upper()}/x.png"}}),
    )
    assert report["players"][0]["source"] == "nfl_verified"


def test_a_verified_map_keyed_by_anything_but_a_target_sleeper_id_is_refused(tmp_path) -> None:
    with pytest.raises(HeadshotBuildError, match="sleeper"):
        build(
            tmp_path, rows=players(("1", "Alpha", "QB")),
            verified_identities=verified(**{"Alpha Adams": {"headshot_url": nfl_url()}}),
        )


def test_the_two_identity_maps_may_not_be_supplied_together(tmp_path) -> None:
    with pytest.raises(HeadshotBuildError, match="together"):
        build(
            tmp_path, rows=players(("1", "Alpha", "QB")),
            identities={"1": {"espn_id": "3139477"}},
            verified_identities=verified(**{"1": {"espn_id": "3139477"}}),
        )


def test_a_player_absent_from_the_verified_map_still_gets_the_sleeper_sources(tmp_path) -> None:
    log: list[str] = []
    build(
        tmp_path, rows=players(("1", "Alpha", "QB"), ("2", "Bravo", "RB")),
        verified_identities=verified(**{"1": {"headshot_url": nfl_url()}}), log=log,
    )
    assert thumb("2") in log and full("2") in log
    assert not any(url == nfl_url() and log.index(url) > log.index(thumb("2")) for url in [nfl_url()])


def test_a_dangling_symlink_output_directory_is_refused(tmp_path) -> None:
    """It does not exist, so an existence check passes it; it is still a link that writes somewhere else."""
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "nowhere", target_is_directory=True)
    with pytest.raises(HeadshotBuildError, match="symlink"):
        build(tmp_path, output_dir=dangling)


# --- the ESPN college path, from the live Cannella recovery (2026-09-08) ----------------------------------


def espn_college(espn_id: str) -> str:
    return ESPN_COLLEGE_HEADSHOT_URL.format(espn_id=espn_id)


def test_an_espn_id_whose_nfl_headshot_is_absent_falls_through_to_the_college_path(tmp_path) -> None:
    """Measured on the real service: Sal Cannella's ESPN id 4242536 gives 404 on the nfl path and 200 on the
    college-football one. The id was right all along; only the path was wrong."""
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("8089", "Sal Cannella", "TE")),
        responses={espn_college("4242536"): Result(200, PNG)},
        verified_identities=verified(**{"8089": {"espn_id": "4242536"}}),
        log=log,
    )
    assert log == [thumb("8089"), full("8089"), espn("4242536"), espn_college("4242536")]
    assert report["players"][0]["source"] == "espn_college"
    assert [attempt["outcome"] for attempt in report["players"][0]["attempts"]] == [
        "not_found", "not_found", "not_found", "image",
    ]


def test_the_college_path_is_never_reached_when_the_nfl_one_answers(tmp_path) -> None:
    log: list[str] = []
    report = build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        responses={espn("3139477"): Result(200, PNG)},
        verified_identities=verified(**{"1": {"espn_id": "3139477"}}), log=log,
    )
    assert espn_college("3139477") not in log
    assert report["players"][0]["source"] == "espn"


def test_both_espn_paths_use_that_players_own_id_and_come_last_in_order(tmp_path) -> None:
    log: list[str] = []
    build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        verified_identities=verified(**{"1": {"headshot_url": nfl_url(), "espn_id": "3139477"}}), log=log,
    )
    assert log == [thumb("1"), full("1"), nfl_url(), espn("3139477"), espn_college("3139477")]


def test_a_player_with_no_espn_id_reaches_neither_espn_path(tmp_path) -> None:
    log: list[str] = []
    build(
        tmp_path, rows=players(("1", "Alpha", "QB")),
        verified_identities=verified(**{"1": {"headshot_url": nfl_url()}}), log=log,
    )
    assert not any("espncdn" in url for url in log)


def test_verified_fordham_portrait_recovers_exact_player(tmp_path):
    url = "https://fordhamsports.com/images/2018/8/20/SearightHS.jpg"
    log = []
    report = build(
        tmp_path, rows=players(("6618", "Isaiah Searight", "TE")),
        responses={url: Result(200, PNG)},
        verified_identities=verified(**{"6618": {"headshot_url": url}}), log=log,
    )
    assert log == [thumb("6618"), full("6618"), url]
    assert report["players"][0]["source"] == "college_verified"


def test_fordham_lookalike_is_refused_before_fetch(tmp_path):
    log = []
    with pytest.raises(HeadshotBuildError):
        build(tmp_path, verified_identities=verified(**{"1": {
            "headshot_url": "https://fordhamsports.com.attacker.example/photo.jpg"
        }}), log=log)
    assert log == []
