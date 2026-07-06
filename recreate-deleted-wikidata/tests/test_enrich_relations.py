"""Unit tests for the pure relation-parsing logic in enrich_relations."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import enrich_relations as r  # noqa: E402

WT = (
    "{{Infobox person|gender={{ill|Male (gender)|qid=Q6581097}}|birth=1110}}\n"
    "| Siblings = {{ill|Abe no Masafumi|ja|安倍政文|qid=DELETED_QID}}, "
    "'''Abe no Yasuchika''', {{ill|Abe no Yasutoshi|ja|安倍泰時|qid=DELETED_QID}}\n"
    "| Children = {{ill|Abe no Kiyohiro|ja|安倍季弘|qid=DELETED_QID}}\n"
    "'''Abe no Yasuchika''' (安倍泰親) was an onmyoji.\n"
    "* Father: {{ill|Abe no Yasunaga|ja|安倍泰長}}\n"
    "* Mother: {{ill|Takahashi's daughter|ja|高階有長娘}}\n"
)


def test_targets_in_parses_ill_and_links():
    got = r._targets_in("{{ill|Abe no Kiyohiro|ja|安倍季弘|qid=DELETED_QID}}, [[Abe no Yasunaga]]")
    assert ("Abe no Kiyohiro", "安倍季弘") in got
    assert ("Abe no Yasunaga", "") in got


def test_host_sex_male():
    assert r.host_sex(WT) == "male"


def test_host_ja():
    assert r.host_ja(WT) == "安倍泰親"


def test_candidate_child_of_male_host():
    assert r.classify_candidate("Abe no Kiyohiro", "安倍季弘", WT) == "child_of_host_male"


def test_candidate_sibling():
    assert r.classify_candidate("Abe no Masafumi", "安倍政文", WT) == "sibling_of_host"


def test_candidate_father():
    assert r.classify_candidate("Abe no Yasunaga", "安倍泰長", WT) == "father_of_host"


def test_candidate_mother():
    assert r.classify_candidate("Takahashi's daughter", "高階有長娘", WT) == "mother_of_host"


def test_candidate_unrelated_is_none():
    assert r.classify_candidate("Some Stranger", "無関係の人", WT) is None


FT = (
    "{{familytree/start}}\n"
    "{{familytree |border=0|||||||01||||| 01='''{{ill|Kamibe Shinobi|ja|神部忍|12=simple}}'''}}\n"
    "{{familytree |border=0| |||||||!||||||}}\n"
    "{{familytree |border=0|||||||01||||| 01='''{{ill|Kamibe Kige|ja|神部伎閇|qid=DELETED_QID}}'''}}\n"
    "{{familytree |border=0| |||||||!||||||}}\n"
    "{{familytree |border=0|||||||01||||| 01='''{{ill|Ōkuninushi|en|Ōkuninushi|qid=Q276944}}'''}}\n"
    "{{familytree/end}}\n"
)


def test_familytree_chain_is_ordered():
    chain = r.familytree_chain(FT)
    assert [c[1] for c in chain] == ["神部忍", "神部伎閇", ""]  # 3rd node has no ja
    assert chain[2][2] == "Q276944"  # real qid captured, DELETED_QID dropped
    assert chain[1][2] == ""         # Kamibe Kige's qid=DELETED_QID → no qid


def test_familytree_relation_parent_and_child():
    parent, child = r.familytree_relation("Kamibe Kige", "神部伎閇", FT)
    assert parent[1] == "神部忍"                 # node above = father
    assert child[0] == "Ōkuninushi" and child[2] == "Q276944"  # node below = child, qid


def test_parents_field_variant():
    wt = "| parents = Father: {{ill|Mutō Yorisuke|ja|武藤頼佐|qid=DELETED_QID}}; Mother: X\n"
    assert r.classify_candidate("Mutō Yorisuke", "武藤頼佐", wt) == "father_of_host"


def test_daughter_of_is_not_a_direct_parent():
    # 'Mother: Daughter of X' → X is a grand-parent, NOT the host's parent.
    wt = "| parents = Father: Y; Mother: Daughter of {{ill|Mutō Yorisuke|ja|武藤頼佐|qid=DELETED_QID}}\n"
    assert r.classify_candidate("Mutō Yorisuke", "武藤頼佐", wt) is None


def test_host_wikidata_qid_from_declared_link():
    # Authoritative host QID comes from the article's own {{wikidata link}}, not search.
    assert r.host_wikidata_qid("{{wikidata link|Q11450335}}\nbody") == "Q11450335"
    assert r.host_wikidata_qid("{{Infobox|wikidata=Q123}}") == "Q123"
    assert r.host_wikidata_qid("no wikidata here") is None


def test_child_property_mapping():
    prop, label, sex = r.REL_PROP["child_of_host_male"]
    assert prop == "P22" and label == "father" and sex == "Q6581097"
    prop, label, sex = r.REL_PROP["sibling_of_host"]
    assert prop == "P3373" and label == "sibling"
