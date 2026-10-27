import unittest
import pandas as pd

from src.crawler import canonical_article_url
from src.pipeline import Retriever, chunk_text, prepare_chunks


class CivilRAGTests(unittest.TestCase):
    def test_only_wikibooks_article_urls_are_accepted(self):
        good = canonical_article_url("https://en.wikibooks.org/wiki/Soil_Mechanics?oldid=1#section")
        self.assertEqual(good, "https://en.wikibooks.org/wiki/Soil_Mechanics")
        self.assertIsNone(canonical_article_url("https://example.com/wiki/Soil_Mechanics"))
        self.assertIsNone(canonical_article_url("https://en.wikibooks.org/w/index.php?title=Soil_Mechanics"))
        self.assertIsNone(canonical_article_url("https://en.wikibooks.org/wiki/Special:Search"))

    def test_chunking_returns_text(self):
        text = " ".join([f"civilword{i}" for i in range(400)])
        chunks = chunk_text(text, chunk_words=100, overlap=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))
        self.assertLessEqual(max(len(chunk.split()) for chunk in chunks), 100)

    def test_retrieval_returns_relevant_source(self):
        pages = [
            {
                "title": "Soil Mechanics",
                "url": "https://en.wikibooks.org/wiki/Soil_Mechanics",
                "text": "Soil mechanics studies soil properties, clay, water content, consolidation, and foundation behavior. " * 8,
            },
            {
                "title": "Transportation",
                "url": "https://en.wikibooks.org/wiki/Fundamentals_of_Transportation",
                "text": "Transportation engineering studies traffic flow, road networks, transit demand, and geometric design. " * 8,
            },
        ]
        chunks = prepare_chunks(pages)
        results = Retriever(chunks).search("soil mechanics clay water content", top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "Soil Mechanics")
        self.assertTrue(results[0]["url"].startswith("https://en.wikibooks.org/"))


if __name__ == "__main__":
    unittest.main()
