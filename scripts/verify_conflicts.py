import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity import compute_name_confidence as compute_fuzzy_score


def flag_identity_conflicts(source_player: dict, candidate_player: dict) -> str:
    """Evaluate two player records for potential identity conflicts.

    Returns 'VERIFIED', 'CONFLICT', or 'PENDING'.
    Wrapper kept here so the verification script doesn't need to change its call sites.
    """
    name_score = compute_fuzzy_score(source_player["full_name"], candidate_player["full_name"])
    if name_score >= 0.95:
        src_year = source_player.get("birth_year")
        cand_year = candidate_player.get("birth_year")
        if src_year and cand_year and src_year != cand_year:
            return "CONFLICT"
        return "VERIFIED"
    if name_score >= 0.85:
        return "PENDING"
    return "CONFLICT"

def test_conflicts():
    # Case 1: Same name, same birth year -> VERIFIED
    p1 = {"full_name": "Josh Allen", "birth_year": 1996}
    p2 = {"full_name": "Joshua Allen", "birth_year": 1996}
    print(f"Match 1 (Josh Allen 1996 vs Joshua Allen 1996): {flag_identity_conflicts(p1, p2)}")

    # Case 2: Same name, different birth year -> CONFLICT
    # (e.g. Josh Allen QB BUF vs Josh Allen DE JAX - though they have different positions usually, 
    # but the task specifically mentions birth year)
    p3 = {"full_name": "Josh Allen", "birth_year": 1996}
    p4 = {"full_name": "Josh Allen", "birth_year": 1997}
    print(f"Match 2 (Josh Allen 1996 vs Josh Allen 1997): {flag_identity_conflicts(p3, p4)}")

    # Case 3: Slightly different name, same birth year -> PENDING (if score > 0.85)
    # Adonai Mitchell vs AD Mitchell was 0.8462, so let's try something else
    p5 = {"full_name": "Christopher Olave", "birth_year": 2000}
    p6 = {"full_name": "Chris Olave", "birth_year": 2000}
    # Chris -> Christopher alias should make this 1.0
    print(f"Match 3 (Christopher Olave vs Chris Olave): {flag_identity_conflicts(p5, p6)}")
    
    # Let's find a PENDING case (0.85 <= score < 0.95)
    # "Kenneth Walker III" vs "Ken Walker"
    # normalize("Kenneth Walker III") -> "kenneth_walker"
    # normalize("Ken Walker") -> "ken_walker"
    # Score between "kenneth_walker" and "ken_walker"
    score = compute_fuzzy_score("Kenneth Walker", "Ken Walker")
    print(f"Score for Kenneth Walker vs Ken Walker: {score:.4f}")
    p7 = {"full_name": "Kenneth Walker", "birth_year": 2000}
    p8 = {"full_name": "Ken Walker", "birth_year": 2000}
    print(f"Match 4 (Kenneth Walker vs Ken Walker): {flag_identity_conflicts(p7, p8)}")

    # Case 5: Typo in name -> PENDING (if score > 0.85)
    p9 = {"full_name": "Joshua Allen", "birth_year": 1996}
    p10 = {"full_name": "Joshua Alen", "birth_year": 1996}
    score_typo = compute_fuzzy_score(p9["full_name"], p10["full_name"])
    print(f"Score for Joshua Allen vs Joshua Alen: {score_typo:.4f}")
    print(f"Match 5 (Joshua Allen vs Joshua Alen): {flag_identity_conflicts(p9, p10)}")

if __name__ == "__main__":
    test_conflicts()
