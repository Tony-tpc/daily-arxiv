"""Regression tests for canonical, energy-scoped paper normalization."""

import unittest

from src.sources.paper_normalizer import normalize_paper_records


class PaperNormalizerTests(unittest.TestCase):
    def test_cleans_provider_markup_and_emits_unified_schema(self):
        records = [{
            "id": "W1",
            "title": '&lt;span class="word"&gt;Techno- &lt;b&gt;Economic&lt;/b&gt; Energy Agents',
            "authors": ["Wei Zhang"],
            "categories": ["Energy systems"],
            "entry_url": "https://openalex.org/W1",
            "published": 2026,
        }]

        document = normalize_paper_records(records, "openalex_search", {})[0]

        self.assertEqual(document["title"], "Techno-Economic Energy Agents")
        self.assertEqual(document["source_type"], "paper")
        self.assertEqual(document["source_name"], "OpenAlex")
        self.assertEqual(document["schema_version"], "1.0")
        self.assertEqual(document["authors_or_orgs"], ["Wei Zhang"])
        self.assertEqual(document["published_at"], "2026")

    def test_excludes_robotics_direction_from_energy_intelligence(self):
        records = [{
            "id": "W2",
            "title": "Power dispatch robots using swarm optimization",
            "categories": ["Electric Power System Optimization"],
            "entry_url": "https://openalex.org/W2",
        }]
        config = {"negative_keywords": ["robot", "机械臂"]}

        self.assertEqual(
            normalize_paper_records(records, "openalex_search", config),
            [],
        )

    def test_extracts_bare_arxiv_id_from_openalex_identifier_url(self):
        records = [{
            "id": "2507.01234",
            "title": "Energy Agent Coordination",
            "categories": ["eess.SY"],
            "entry_url": "https://arxiv.org/abs/2507.01234",
        }]

        document = normalize_paper_records(records, "arxiv", {})[0]

        self.assertEqual(document["arxiv_id"], "2507.01234")
        self.assertEqual(document["url"], "https://arxiv.org/abs/2507.01234")


if __name__ == "__main__":
    unittest.main()
