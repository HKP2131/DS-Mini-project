import unittest

import pandas as pd

from src.crawler import canonical_article_url, discover_article_links
from src.pipeline import Retriever, chunk_text, extractive_summary, prepare_chunks


class CivilRAGTests(unittest.TestCase):
    def test_only_wikibooks_article_urls_are_accepted(self):
        good = canonical_article_url(
            "https://en.wikibooks.org/wiki/Soil_Mechanics?oldid=1#section"
        )
        self.assertEqual(good, "https://en.wikibooks.org/wiki/Soil_Mechanics")
        self.assertIsNone(
            canonical_article_url("https://example.com/wiki/Soil_Mechanics")
        )
        self.assertIsNone(
            canonical_article_url("https://en.wikibooks.org/w/index.php?title=Soil_Mechanics")
        )
        self.assertIsNone(
            canonical_article_url("https://en.wikibooks.org/wiki/Special:Search")
        )
        self.assertIsNone(
            canonical_article_url("https://en.wikibooks.org/wiki/Category:Book")
        )

    def test_link_discovery_stays_inside_allowed_book(self):
        html = """
        <div id="mw-content-text">
          <a href="/wiki/Fundamentals_of_Transportation/Traffic_Flow">Traffic flow</a>
          <a href="/wiki/Soil_Mechanics">Soil mechanics</a>
          <a href="https://example.com/wiki/Fundamentals_of_Transportation/Traffic_Flow">external</a>
          <a href="/wiki/Category:Book:Transportation">category</a>
        </div>
        """
        links = discover_article_links(
            html,
            "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation",
            allowed_prefixes=["/wiki/Fundamentals_of_Transportation"],
        )
        self.assertEqual(
            links,
            ["https://en.wikibooks.org/wiki/Fundamentals_of_Transportation/Traffic_Flow"],
        )

    def test_chunking_returns_text(self):
        text = " ".join(f"civilword{i}" for i in range(400))
        chunks = chunk_text(text, chunk_words=100, overlap=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))
        self.assertLessEqual(max(len(chunk.split()) for chunk in chunks), 100)

    def sample_pages(self):
        return [
            {
                "title": "Soil Mechanics",
                "url": "https://en.wikibooks.org/wiki/Soil_Mechanics",
                "text": (
                    "Soil mechanics studies soil properties, clay, water content, "
                    "consolidation, and foundation behavior. "
                )
                * 8,
            },
            {
                "title": "Fundamentals of Transportation",
                "url": "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation",
                "text": (
                    "Transportation engineering studies traffic flow, road networks, "
                    "transit demand, and geometric design. "
                )
                * 8,
            },
        ]

    def test_retrieval_returns_relevant_source(self):
        chunks = prepare_chunks(self.sample_pages())
        results = Retriever(chunks).search(
            "soil mechanics clay water content", top_k=2
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "Soil Mechanics")
        self.assertTrue(results[0]["url"].startswith("https://en.wikibooks.org/"))

    def test_unrelated_question_returns_no_false_match(self):
        chunks = prepare_chunks(self.sample_pages())
        results = Retriever(chunks).search(
            "Who is Taylor Swift and what is the climate history of Mars?", top_k=4
        )
        self.assertEqual(results, [])

    def test_extractive_summary_uses_source_sentences(self):
        pages = self.sample_pages()
        chunks = prepare_chunks(pages)
        results = Retriever(chunks).search("soil mechanics clay water content", top_k=2)
        summary = extractive_summary("soil mechanics clay water content", results)
        self.assertTrue(summary)
        source_texts = [page["text"] for page in pages]
        for item in summary:
            self.assertTrue(any(item["sentence"] in text for text in source_texts))
            self.assertTrue(item["url"].startswith("https://en.wikibooks.org/"))


if __name__ == "__main__":
    unittest.main()
