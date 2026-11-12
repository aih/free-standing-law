import unittest

from tools.uncodified.citations import key_of, parse_credit, parse_note_citation
from tools.uncodified.analyze import cite


class Credits(unittest.TestCase):
    def test_public_law_sections_across_titles(self):
        got = parse_credit("(Pub. L. 98–353, title III, §§ 304, 363(b), title IV, § 401, "
                           "July 10, 1984, 98 Stat. 352, 363)")
        self.assertEqual(got, [("/us/pl/98/353", None, "304"), ("/us/pl/98/353", None, "363"),
                               ("/us/pl/98/353", None, "401")])

    def test_added_and_amended(self):
        got = parse_credit("(Added Pub. L. 103–394, title III, § 308(a), Oct. 22, 1994, 108 Stat. 4135; "
                           "amended Pub. L. 109–8, title II, § 221, title XII, § 1205, Apr. 20, 2005, 119 Stat. 59, 194.)")
        self.assertEqual(got, [("/us/pl/103/394", None, "308"), ("/us/pl/109/8", None, "221"),
                               ("/us/pl/109/8", None, "1205")])

    def test_division(self):
        got = parse_credit("(Pub. L. 105–277, div. I, title VI, § 603, Oct. 21, 1998, 112 Stat. 2681–886)")
        self.assertEqual(got, [("/us/pl/105/277", "I", "603")])

    def test_act_by_date_and_chapter_and_revised_statutes(self):
        got = parse_credit("(R.S. § 4813; June 15, 1943, ch. 125, § 3, 57 Stat. 153; "
                           "Mar. 2, 1907, ch. 2511, 34 Stat. 1172.)")
        self.assertEqual(got, [("R.S.", None, "4813"), ("/us/act/1943-06-15/ch125", None, "3"),
                               ("/us/act/1907-03-02/ch2511", None, None)])

    def test_act_credited_without_a_section(self):
        self.assertEqual(parse_credit("(Pub. L. 95–598, Nov. 6, 1978, 92 Stat. 2570.)"),
                         [("/us/pl/95/598", None, None)])

    def test_enacted_by_reference_keys_the_enacting_section(self):
        got = parse_credit("(Pub. L. 106–398, § 1 [[div. A], title IX, § 902], Oct. 30, 2000, 114 Stat. 1654)")
        self.assertEqual(got, [("/us/pl/106/398", None, "1")])


class Notes(unittest.TestCase):
    def test_set_out_as_amended_names_the_provision_not_the_amender(self):
        t = ("Pub. L. 95–598, title IV, § 402, Nov. 6, 1978, 92 Stat. 2682, as amended by "
             "Pub. L. 98–353, title I, §§ 113, 121(a), July 10, 1984, 98 Stat. 343, provided that:")
        self.assertEqual(parse_note_citation(t), [("/us/pl/95/598", None, "402")])

    def test_range(self):
        t = "Pub. L. 98–353, title III, §§ 551–553, July 10, 1984, 98 Stat. 392, provided that:"
        self.assertEqual([k[2] for k in parse_note_citation(t)], ["551", "552", "553"])


    def test_formerly_names_the_section_as_enacted(self):
        t = "Pub. L. 98–353, title III, § 552, formerly § 553, July 10, 1984, 98 Stat. 392, provided that:"
        self.assertEqual(parse_note_citation(t), [("/us/pl/98/353", None, "553")])


class Identifiers(unittest.TestCase):
    def test_key_of(self):
        self.assertEqual(key_of("/us/pl/109/8/tI/s102/e"), ("/us/pl/109/8", None, "102"))
        self.assertEqual(key_of("/us/pl/105/277/dI/tVI/s603"), ("/us/pl/105/277", "I", "603"))
        self.assertEqual(key_of("/us/act/1943-06-15/ch125/s3"), ("/us/act/1943-06-15/ch125", None, "3"))

    def test_cite(self):
        self.assertEqual(cite("/us/usc/t28/s2075"), "28 U.S.C. 2075")
        self.assertEqual(cite("/us/usc/t28/ptI/ch6"), "28 U.S.C. ch. 6")
        self.assertEqual(cite("/us/usc/t11"), "title 11")


if __name__ == "__main__":
    unittest.main()
